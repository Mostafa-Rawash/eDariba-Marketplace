"""Public accountant-directory endpoints.

Routes (once this app is installed on the real site):
  GET /api/method/edariba_marketplace.api.public.accountants.list_accountants
  GET /api/method/edariba_marketplace.api.public.accountants.get_accountant
"""

import frappe

from edariba_marketplace.api.public.common import ok
from edariba_marketplace.services import repository
from edariba_marketplace.services.filters import (
	ACCOUNTANT_SORT_FIELDS,
	clamp_page,
	clamp_page_size,
	names_matching_tag,
	resolve_sort,
)


@frappe.whitelist(allow_guest=True)
def list_accountants(
	q: str = "",
	specialty: str = "",
	governorate: str = "",
	category: str = "",
	page: int = 1,
	page_size: int = 20,
	sort_by: str = "experience_years",
	sort_order: str = "desc",
):
	page = clamp_page(page)
	page_size = clamp_page_size(page_size)
	order_by = resolve_sort(sort_by, sort_order, ACCOUNTANT_SORT_FIELDS, "experience_years")

	filters: dict = {}
	if governorate:
		filters["governorate"] = governorate

	if specialty:
		matching = names_matching_tag("Marketplace Profile", "specialties", specialty)
		if not matching:
			return ok([], page=page, page_size=page_size, total=0, meta={"q": q, "specialty": specialty})
		filters["name"] = ["in", matching]

	rows, total = repository.list_profiles(filters, order_by, page, page_size)

	if q:
		q_lower = q.lower()
		rows = [r for r in rows if q_lower in (r.display_name or "").lower() or q_lower in (r.headline or "").lower()]

	return ok(rows, page=page, page_size=page_size, total=total, meta={"q": q, "specialty": specialty, "governorate": governorate})


@frappe.whitelist(allow_guest=True)
def get_accountant(slug: str):
	profile = repository.get_profile_by_slug(slug)
	profile["published_services"] = repository.published_services_for_provider(profile["name"])
	return ok(profile)
