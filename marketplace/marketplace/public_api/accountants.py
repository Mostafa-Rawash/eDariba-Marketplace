"""Public accountant-directory endpoints.

Routes (once this app is installed on the real site):
  GET /api/method/marketplace.marketplace.public_api.accountants.list_accountants
  GET /api/method/marketplace.marketplace.public_api.accountants.get_accountant
"""

import frappe

from marketplace.shared.responses import ok
from marketplace.activity import events
from marketplace.marketplace import repository
from marketplace.shared.filters import (
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

	or_filters = repository.text_search(q, ["display_name", "headline"])
	rows, total = repository.list_profiles(filters, order_by, page, page_size, or_filters)

	meta = {"q": q, "specialty": specialty, "governorate": governorate}
	meta.update(events.search_meta(q, ["accountant"], [("accountant", r["name"]) for r in rows], total, page))
	return ok(rows, page=page, page_size=page_size, total=total, meta=meta)


SERVICES_SHOWN = 20


@frappe.whitelist(allow_guest=True)
def get_accountant(slug: str):
	profile = repository.get_profile_by_slug(slug)
	services = repository.published_services_for_provider(profile["name"], limit=SERVICES_SHOWN)
	profile["published_services"] = services
	# published_services is the first page; the count shown on the profile
	# must use this total, which is only counted when the page is full.
	profile["published_services_total"] = (
		repository.count_published_services(profile["name"]) if len(services) == SERVICES_SHOWN else len(services)
	)
	return ok(profile)
