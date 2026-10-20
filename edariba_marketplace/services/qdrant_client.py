"""Thin wrapper over the Qdrant REST API.

Verified live and unauthenticated against the real instance:
  2026-10-14: GET {QDRANT_URL}/, GET .../collections (listed collection_name,
    edariba_knowledge_base, accountants, client_assistant, invoices,
    search_keywords, edariba_marketplace). PUT .../points (upsert) -> point
    "id" MUST be an unsigned integer or a UUID — a plain string like
    "Marketplace Profile:acc-01" is REJECTED with 400 "not a valid point ID".
    indexing_service._point_id() uses uuid5 to turn (doctype, name) into a
    deterministic UUID instead. Full embed -> upsert -> search -> delete
    round trip verified live and cleaned up.
  2026-10-15: switched from one shared "edariba_marketplace" collection to
    one collection per entity type (config.qdrant_collection_for). Created
    "services" and "projects" (1024-dim, Cosine, did not exist before).
    "accountants" already existed with 20 unrelated real records (different
    schema, no "status" payload key, integer ids 1-20) — reusing it was an
    explicit decision despite the mismatch; see config.py for the full note.

This module only talks to Qdrant — it never calls the embedding API and never
touches Frappe documents. Every function below now REQUIRES a `collection`
argument — there is no single-collection default anymore, so a caller that
forgets to pass one fails immediately instead of silently hitting the wrong
collection.
"""

from typing import Any

import frappe
import requests

from edariba_marketplace.services.config import (
	http_timeout_seconds,
	qdrant_url,
)


class QdrantError(frappe.ValidationError):
	pass


def _request(method: str, path: str, **kwargs) -> dict[str, Any]:
	url = f"{qdrant_url()}{path}"
	try:
		resp = requests.request(method, url, timeout=http_timeout_seconds(), **kwargs)
	except requests.exceptions.Timeout:
		frappe.log_error(title="Qdrant timeout", message=f"{method} {path}")
		raise QdrantError("Search is temporarily unavailable (timeout).")
	except requests.exceptions.RequestException as exc:
		frappe.log_error(title="Qdrant request failed", message=f"{method} {path}: {exc}")
		raise QdrantError("Search is temporarily unavailable.")

	if resp.status_code >= 500:
		frappe.log_error(title="Qdrant 5xx", message=f"{method} {path}: {resp.status_code}")
		raise QdrantError("Search is temporarily unavailable.")
	if resp.status_code >= 400:
		# 4xx here is a programming error (bad filter, bad vector size), not a
		# transient outage — surface it rather than masking it as "unavailable".
		frappe.throw(f"Qdrant rejected the request ({resp.status_code}): {resp.text[:300]}")

	return resp.json()


def collection_vector_size(collection: str) -> int:
	info = _request("GET", f"/collections/{collection}")
	return info["result"]["config"]["params"]["vectors"]["size"]


def upsert_points(points: list[dict[str, Any]], collection: str) -> None:
	"""Each point: {"id": <str|int>, "vector": [...], "payload": {...}}."""
	if not points:
		return
	_request("PUT", f"/collections/{collection}/points?wait=true", json={"points": points})


def delete_points(point_ids: list[str | int], collection: str) -> None:
	if not point_ids:
		return
	_request(
		"POST",
		f"/collections/{collection}/points/delete?wait=true",
		json={"points": point_ids},
	)


def search(
	vector: list[float],
	collection: str,
	limit: int = 10,
	query_filter: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
	"""Returns Qdrant's raw result rows: [{"id":..., "score":..., "payload":{...}}, ...].
	Callers (search_service.py) are responsible for treating these as
	candidates only and revalidating against Frappe before returning them."""
	body: dict[str, Any] = {
		"vector": vector,
		"limit": max(1, min(int(limit), 50)),
		"with_payload": True,
	}
	if query_filter:
		body["filter"] = query_filter
	result = _request("POST", f"/collections/{collection}/points/search", json=body)
	return result.get("result", [])
