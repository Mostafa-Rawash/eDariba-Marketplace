"""Unified semantic search, including the "AI assistant" box.

Route:
  POST /api/method/edariba_marketplace.api.public.search.search

`auto_intent=1` is the former chat.discover endpoint, merged in here
(2026-10-20): instead of the caller choosing entity_types, a deterministic
keyword router (services/intent_router.py, not an LLM) picks the entity
type and, when it recognises one, a category. Retrieval is the same either
way.

Raises a clear EmbeddingError, not a fake empty success, while
EMBEDDING_API_KEY is not configured.
"""

import frappe
from frappe.utils import sbool

from edariba_marketplace.api.common import ok
from edariba_marketplace.services.filters import clamp_page, clamp_page_size
from edariba_marketplace.services.intent_router import classify
from edariba_marketplace.services.search_service import search as run_search


@frappe.whitelist(allow_guest=True)
def search(
	query: str,
	entity_types: list | None = None,
	filters: dict | None = None,
	page: int = 1,
	page_size: int = 10,
	auto_intent: bool = False,
):
	if not query or not query.strip():
		frappe.throw("query is required.")

	page = clamp_page(page)
	page_size = clamp_page_size(page_size, default=10, maximum=25)
	filters = dict(filters or {})

	intent = None
	if sbool(auto_intent):
		intent = classify(query)
		if not entity_types:
			entity_types = [intent["entity_type"]]
		if intent["category"]:
			filters.setdefault("category", intent["category"])

	result = run_search(query, entity_types, filters, page, page_size)

	meta = {"query": query, "entity_types": result["entity_types"], "applied_filters": result["applied_filters"]}
	if intent is not None:
		meta["intent_matched"] = intent["matched"]
	return ok(result["results"], page=page, page_size=page_size, total=result["total"], meta=meta)
