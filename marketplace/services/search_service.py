"""Unified semantic search across accountant/service/project, per the flow
in the task brief: Qdrant finds candidates, Frappe is the only authority on
whether they still exist and are still public.

As of 2026-10-15 each entity type lives in its own Qdrant collection
(config.qdrant_collection_for) rather than one shared collection
distinguished by an "entity_type" payload field. A "unified" search across
multiple types is therefore a fan-out: one /points/search call per
requested collection, merged by score afterwards — Qdrant has no
cross-collection query, so this is unavoidable, not a shortcut.
"""

import frappe

from marketplace.services import qdrant_client, repository
from marketplace.services.config import qdrant_collection_for
from marketplace.services.embedding_client import embed_text

ENTITY_TYPES = {"accountant", "service", "project"}

_PUBLIC_LOOKUP = {
	# All three DocTypes use autoname "field:slug", so the Qdrant payload's
	# "frappe_name" (== doc.name) is always equal to the slug — the existing
	# get_*_by_slug repository functions are the correct lookup as-is.
	"accountant": ("Marketplace Profile", repository.get_profile_by_slug),
	"service": ("Marketplace Service", repository.get_service_by_slug),
	"project": ("Marketplace Project", repository.get_project_by_slug),
}


def _public_record(entity_type: str, slug: str) -> dict | None:
	"""The published record behind a Qdrant hit, or None when it was deleted or
	unpublished since it was indexed (or never existed in Frappe). Checks
	existence first instead of catching the getter's error: frappe.throw
	queues its "not found" message into the response even when the exception
	is caught, and the client would show it as an error."""
	doctype, getter = _PUBLIC_LOOKUP[entity_type]
	if not frappe.db.exists(doctype, {"slug": slug, "publication_status": "Published"}):
		return None
	return getter(slug)


def validate_entity_types(entity_types: list[str] | None) -> list[str]:
	if not entity_types:
		return sorted(ENTITY_TYPES)
	cleaned = [e for e in entity_types if e in ENTITY_TYPES]
	if not cleaned:
		frappe.throw(f"entity_types must be a subset of {sorted(ENTITY_TYPES)}")
	return cleaned


def build_qdrant_filter(filters: dict) -> dict:
	"""Allowlisted mapping of public filter names onto indexed Qdrant payload
	fields only — never pass client-supplied keys through verbatim. No
	"entity_type" clause anymore: which collection we query already decides
	that. "status" stays as a defensive filter even though indexing_service
	deletes a point the moment a record is unpublished — belt and suspenders
	against a late-arriving stale point from a retried job."""
	must: list[dict] = [{"key": "status", "match": {"value": "Published"}}]

	location = filters.get("location")
	if location:
		must.append({"key": "service_area", "match": {"value": location}})

	specialty = filters.get("specialty")
	if specialty:
		values = specialty if isinstance(specialty, list) else [specialty]
		must.append({"key": "specialization_ids", "match": {"any": values}})

	return {"must": must}


def _search_one_entity_type(entity_type: str, vector: list[float], qdrant_filter: dict, raw_limit: int) -> list[dict]:
	collection = qdrant_collection_for(entity_type)
	rows = qdrant_client.search(vector, collection, limit=raw_limit, query_filter=qdrant_filter)

	results = []
	for row in rows:
		payload = row.get("payload") or {}
		frappe_name = payload.get("frappe_name")
		if not frappe_name:
			continue
		record = _public_record(entity_type, frappe_name)
		if record is None:
			continue  # deleted or unpublished since the point was indexed
		results.append({"entity_type": entity_type, "score": row.get("score"), **record})
	return results


def search(query: str, entity_types: list[str] | None, filters: dict | None, page: int, page_size: int) -> dict:
	if not query or not query.strip():
		frappe.throw("query is required.")

	entity_types = validate_entity_types(entity_types)
	filters = filters or {}
	qdrant_filter = build_qdrant_filter(filters)

	vector = embed_text(query)
	# Over-fetch before pagination: some candidates will be dropped on
	# Frappe revalidation (stale/unpublished since last index), so asking
	# Qdrant for exactly page_size would under-fill the page. Each collection
	# is queried for this same raw_limit independently, then merged.
	raw_limit = min(page * page_size * 2, 100)

	results: list[dict] = []
	for entity_type in entity_types:
		results.extend(_search_one_entity_type(entity_type, vector, qdrant_filter, raw_limit))

	results.sort(key=lambda r: r.get("score") or 0, reverse=True)

	start = (page - 1) * page_size
	page_results = results[start : start + page_size]

	return {
		"results": page_results,
		"total": len(results),
		"applied_filters": filters,
		"entity_types": entity_types,
	}
