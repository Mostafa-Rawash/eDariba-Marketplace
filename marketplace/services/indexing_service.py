"""Keeps the per-entity-type Qdrant collections (config.qdrant_collection_for)
in sync with published Marketplace Profile/Service/Project records — one
collection each: "marketplace_accountants", "marketplace_services",
"marketplace_projects" (see config.py).

RECONCILIATION NOTE — read before changing payload field names below.
These field names were chosen against the originally-discovered
"edariba_marketplace" shared collection's pre-existing payload schema, which
does not line up cleanly with the DocTypes built from the actual WordPress
UI in this task. That reconciliation still applies even after the move to
per-entity collections — the field semantics below didn't change, only
which collection each entity's points live in:

  pre-existing field      type      our situation
  -----------------      -------   --------------------------------------
  entity_type             keyword   OK — we set "accountant"/"service"/"project"
  accountant_id           integer   MISMATCH. Marketplace Profile is named by
                                     slug (string), not an integer id. We do
                                     NOT invent a fake integer here — we add
                                     a separate `frappe_name` keyword field
                                     (the real doc name) instead and leave
                                     accountant_id unset. Whoever owns this
                                     collection needs to decide whether to
                                     re-create it with a string id field, or
                                     tell us the integer id source.
  slug                     keyword   OK
  service_area             keyword   APPROXIMATION — we have governorate+area,
                                     not a single "service_area"; we send
                                     governorate.
  specialization_ids       keyword   APPROXIMATION — Marketplace Profile has
                                     free-text specialty labels (Marketplace
                                     Tag), not controlled IDs. We send the
                                     labels. Rename on the Qdrant side (or add
                                     a real taxonomy) if true IDs are needed.
  service_ids              keyword   OK — real Marketplace Service names for
                                     this provider.
  languages                keyword   NOT POPULATED. The `languages` field was
                                     deliberately removed from the WordPress
                                     UI earlier in this project; there is no
                                     source data for it. Omitted, not sent as
                                     an empty placeholder.
  experience_years         integer   OK
  status                   keyword   OK — publication_status
  updated_at                integer  OK — doc.modified as epoch seconds
  schema_version            integer  OK — SCHEMA_VERSION constant below

Indexing runs via frappe.enqueue (background job), never inline in a
document save — an embedding-service outage must not block or roll back a
Marketplace Profile/Service/Project save. See hooks.py doc_events.
"""

import time
import uuid

import frappe

from marketplace.services import qdrant_client
from marketplace.services.config import qdrant_collection_for
from marketplace.services.embedding_client import embed_text

SCHEMA_VERSION = 1
QUEUE = "short"

_DOCTYPE_ENTITY_TYPE = {
	"Marketplace Profile": "accountant",
	"Marketplace Service": "service",
	"Marketplace Project": "project",
}


# ------------------------------------------------------------- payload ---

def _epoch(doc) -> int:
	return int(time.mktime(doc.modified.timetuple())) if doc.modified else int(time.time())


def build_profile_payload(doc) -> dict:
	return {
		"entity_type": "accountant",
		"frappe_name": doc.name,  # see RECONCILIATION NOTE — not accountant_id
		"slug": doc.slug,
		"service_area": doc.governorate,
		"specialization_ids": [row.label for row in doc.specialties],
		"service_ids": [
			r.name
			for r in frappe.get_all(
				"Marketplace Service", filters={"provider": doc.name, "publication_status": "Published"}
			)
		],
		"experience_years": doc.experience_years,
		"status": doc.publication_status,
		"updated_at": _epoch(doc),
		"schema_version": SCHEMA_VERSION,
	}


def build_profile_text(doc) -> str:
	parts = [doc.display_name, doc.headline, doc.bio]
	parts += [row.label for row in doc.specialties]
	return "\n".join(p for p in parts if p)


def build_service_payload(doc) -> dict:
	return {
		"entity_type": "service",
		"frappe_name": doc.name,
		"slug": doc.slug,
		"category": doc.category,
		"provider": doc.provider,
		"status": doc.publication_status,
		"updated_at": _epoch(doc),
		"schema_version": SCHEMA_VERSION,
	}


def build_service_text(doc) -> str:
	parts = [doc.title, doc.description]
	parts += [row.label for row in doc.badges] + [row.label for row in doc.features]
	return "\n".join(p for p in parts if p)


def build_project_payload(doc) -> dict:
	return {
		"entity_type": "project",
		"frappe_name": doc.name,
		"slug": doc.slug,
		"category": doc.category,
		"specialization_ids": [row.label for row in doc.required_skills],
		"status": doc.publication_status,
		"updated_at": _epoch(doc),
		"schema_version": SCHEMA_VERSION,
	}


def build_project_text(doc) -> str:
	parts = [doc.title, doc.description] + [row.label for row in doc.required_skills]
	return "\n".join(p for p in parts if p)


# --------------------------------------------------------------- sync ---

_POINT_ID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "marketplace.points")


def _point_id(doctype: str, name: str) -> str:
	"""Qdrant rejects arbitrary strings as point ids — it only accepts an
	unsigned integer or a UUID (confirmed live: PUT .../points with a plain
	string id returns 400 'not a valid point ID'). uuid5 gives a UUID that
	is deterministic and stable across re-indexes for the same (doctype,
	name), which is what we actually need — not literally a random UUID."""
	return str(uuid.uuid5(_POINT_ID_NAMESPACE, f"{doctype}:{name}"))


def _sync(doctype: str, name: str, payload_fn, text_fn):
	doc = frappe.get_doc(doctype, name)
	point_id = _point_id(doctype, name)
	collection = qdrant_collection_for(_DOCTYPE_ENTITY_TYPE[doctype])

	if doc.get("publication_status") != "Published":
		qdrant_client.delete_points([point_id], collection=collection)
		return

	text = text_fn(doc)
	vector = embed_text(text)  # raises EmbeddingError if unconfigured/unreachable
	qdrant_client.upsert_points(
		[{"id": point_id, "vector": vector, "payload": payload_fn(doc)}], collection=collection
	)


def _enqueue(doctype: str, name: str, payload_fn_path: str, text_fn_path: str):
	frappe.enqueue(
		"marketplace.services.indexing_service._sync_by_path",
		queue=QUEUE,
		doctype_name=doctype,
		doc_name=name,
		payload_fn_path=payload_fn_path,
		text_fn_path=text_fn_path,
	)


def _sync_by_path(doctype_name: str, doc_name: str, payload_fn_path: str, text_fn_path: str):
	payload_fn = frappe.get_attr(payload_fn_path)
	text_fn = frappe.get_attr(text_fn_path)
	try:
		_sync(doctype_name, doc_name, payload_fn, text_fn)
	except Exception:
		# A failed embed/upsert must never surface as a failed document save —
		# this already runs in a background job, so just log for reconciliation.
		frappe.log_error(title="Marketplace indexing failed", message=frappe.get_traceback())


def _delete_enqueue(doctype: str, name: str):
	frappe.enqueue(
		"marketplace.services.indexing_service._delete_by_path",
		queue=QUEUE,
		doctype_name=doctype,
		doc_name=name,
	)


def _delete_by_path(doctype_name: str, doc_name: str):
	try:
		collection = qdrant_collection_for(_DOCTYPE_ENTITY_TYPE[doctype_name])
		qdrant_client.delete_points([_point_id(doctype_name, doc_name)], collection=collection)
	except Exception:
		frappe.log_error(title="Marketplace de-index failed", message=frappe.get_traceback())


# ------------------------------------------------------------ doc_events ---

_PATHS = {
	"Marketplace Profile": (
		"marketplace.services.indexing_service.build_profile_payload",
		"marketplace.services.indexing_service.build_profile_text",
	),
	"Marketplace Service": (
		"marketplace.services.indexing_service.build_service_payload",
		"marketplace.services.indexing_service.build_service_text",
	),
	"Marketplace Project": (
		"marketplace.services.indexing_service.build_project_payload",
		"marketplace.services.indexing_service.build_project_text",
	),
}


def on_profile_update(doc, method=None):
	payload_fn, text_fn = _PATHS["Marketplace Profile"]
	_enqueue("Marketplace Profile", doc.name, payload_fn, text_fn)


def on_profile_delete(doc, method=None):
	_delete_enqueue("Marketplace Profile", doc.name)


def on_service_update(doc, method=None):
	payload_fn, text_fn = _PATHS["Marketplace Service"]
	_enqueue("Marketplace Service", doc.name, payload_fn, text_fn)


def on_service_delete(doc, method=None):
	_delete_enqueue("Marketplace Service", doc.name)


def on_project_update(doc, method=None):
	payload_fn, text_fn = _PATHS["Marketplace Project"]
	_enqueue("Marketplace Project", doc.name, payload_fn, text_fn)


def on_project_delete(doc, method=None):
	_delete_enqueue("Marketplace Project", doc.name)


# ------------------------------------------------------- reconciliation ---

@frappe.whitelist()
def reconcile(doctype: str, limit: int = 100):
	"""Manual, on-demand sweep for records missing or stale in Qdrant —
	NOT run automatically (the task is explicit: no automatic bulk reindex
	of production data). A System Manager calls this deliberately, e.g.
	after fixing the embedding key, to catch up a backlog."""
	if "System Manager" not in frappe.get_roles():
		frappe.throw("Not permitted.", frappe.PermissionError)
	if doctype not in _PATHS:
		frappe.throw(f"Unsupported doctype for reconciliation: {doctype}")

	names = frappe.get_all(doctype, filters={"publication_status": "Published"}, pluck="name", limit_page_length=limit)
	payload_fn, text_fn = _PATHS[doctype]
	for name in names:
		_enqueue(doctype, name, payload_fn, text_fn)
	return {"queued": len(names)}
