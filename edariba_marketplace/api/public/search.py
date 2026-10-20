"""Unified semantic search.

Route:
  POST /api/method/edariba_marketplace.api.public.search.search

BLOCKED end-to-end until EMBEDDING_API_KEY is configured and its contract
verified (see services/embedding_client.py) — this endpoint
will raise a clear EmbeddingError, not return fake/empty-looking success,
until that happens.
"""

import frappe

from edariba_marketplace.api.public.common import ok
from edariba_marketplace.services.filters import clamp_page, clamp_page_size
from edariba_marketplace.services.search_service import search as run_search


@frappe.whitelist(allow_guest=True)
def search(query: str, entity_types: list | None = None, filters: dict | None = None, page: int = 1, page_size: int = 10):
	page = clamp_page(page)
	page_size = clamp_page_size(page_size, default=10, maximum=25)
	result = run_search(query, entity_types, filters, page, page_size)
	return ok(
		result["results"],
		page=page,
		page_size=page_size,
		total=result["total"],
		meta={"query": query, "entity_types": result["entity_types"], "applied_filters": result["applied_filters"]},
	)
