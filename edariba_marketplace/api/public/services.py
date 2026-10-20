"""Public services-marketplace endpoints.

Routes:
  GET /api/method/edariba_marketplace.api.public.services.list_services
  GET /api/method/edariba_marketplace.api.public.services.get_service
"""

import frappe

from edariba_marketplace.api.common import ok
from edariba_marketplace.services import repository
from edariba_marketplace.services.filters import (
	SERVICE_SORT_FIELDS,
	clamp_page,
	clamp_page_size,
	resolve_sort,
	validate_price_range,
)


@frappe.whitelist(allow_guest=True)
def list_services(
	q: str = "",
	category: str = "",
	provider: str = "",
	min_price: float | None = None,
	max_price: float | None = None,
	page: int = 1,
	page_size: int = 20,
	sort_by: str = "price",
	sort_order: str = "asc",
):
	validate_price_range(min_price, max_price)
	page = clamp_page(page)
	page_size = clamp_page_size(page_size)
	order_by = resolve_sort(sort_by, sort_order, SERVICE_SORT_FIELDS, "price")

	filters: dict = {}
	if category:
		filters["category"] = category
	if provider:
		filters["provider"] = provider
	if min_price is not None and max_price is not None:
		filters["price"] = ["between", [float(min_price), float(max_price)]]
	elif min_price is not None:
		filters["price"] = [">=", float(min_price)]
	elif max_price is not None:
		filters["price"] = ["<=", float(max_price)]

	rows, total = repository.list_services(filters, order_by, page, page_size, repository.text_search(q, ["title"]))

	return ok(rows, page=page, page_size=page_size, total=total, meta={"q": q, "category": category})


@frappe.whitelist(allow_guest=True)
def get_service(slug: str):
	service = repository.get_service_by_slug(slug)
	provider = frappe.db.get_value(
		"Marketplace Profile", service["provider"], ["display_name", "slug"], as_dict=True
	)
	service["provider_name"] = provider.display_name if provider else None
	service["provider_slug"] = provider.slug if provider else None
	return ok(service)
