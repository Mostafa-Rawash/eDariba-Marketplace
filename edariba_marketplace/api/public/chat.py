"""Chat discovery endpoint for the WordPress "AI assistant" input.

Route:
  POST /api/method/edariba_marketplace.api.public.chat.discover

Intent classification (which entity type(s) to search) is deterministic
keyword matching — see services/intent_router.py — not an LLM.
Retrieval reuses the same semantic search as /search, so it is blocked by
the same EmbeddingError until EMBEDDING_API_KEY is configured.
"""

import frappe

from edariba_marketplace.api.public.common import ok
from edariba_marketplace.services.filters import clamp_page, clamp_page_size
from edariba_marketplace.services.intent_router import classify
from edariba_marketplace.services.search_service import search as run_search


@frappe.whitelist(allow_guest=True)
def discover(message: str, filters: dict | None = None, page: int = 1, page_size: int = 10):
	if not message or not message.strip():
		frappe.throw("message is required.")

	page = clamp_page(page)
	page_size = clamp_page_size(page_size, default=10, maximum=25)

	intent = classify(message)
	filters = dict(filters or {})
	if intent["category"]:
		filters.setdefault("category", intent["category"])

	result = run_search(message, [intent["entity_type"]], filters, page, page_size)

	return ok(
		result["results"],
		page=page,
		page_size=page_size,
		total=result["total"],
		meta={
			"query": message,
			"entity_types": result["entity_types"],
			"applied_filters": result["applied_filters"],
			"intent_matched": intent["matched"],
		},
	)
