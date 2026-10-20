"""Public freelance-projects endpoints.

Routes:
  GET /api/method/marketplace.api.public.projects.list_projects
  GET /api/method/marketplace.api.public.projects.get_project
"""

import frappe

from marketplace.api.common import ok
from marketplace.services import repository
from marketplace.services.filters import (
	PROJECT_SORT_FIELDS,
	clamp_page,
	clamp_page_size,
	names_matching_tag,
	resolve_sort,
	validate_price_range,
)


@frappe.whitelist(allow_guest=True)
def list_projects(
	q: str = "",
	category: str = "",
	skills: str = "",
	budget_min: float | None = None,
	budget_max: float | None = None,
	page: int = 1,
	page_size: int = 20,
	sort_by: str = "deadline",
	sort_order: str = "asc",
):
	validate_price_range(budget_min, budget_max)
	page = clamp_page(page)
	page_size = clamp_page_size(page_size)
	order_by = resolve_sort(sort_by, sort_order, PROJECT_SORT_FIELDS, "deadline")

	filters: dict = {}
	if category:
		filters["category"] = category
	if budget_min is not None:
		filters["budget_min"] = [">=", float(budget_min)]
	if budget_max is not None:
		filters["budget_max"] = ["<=", float(budget_max)]

	if skills:
		matching = names_matching_tag("Marketplace Project", "required_skills", skills)
		if not matching:
			return ok([], page=page, page_size=page_size, total=0, meta={"q": q, "skills": skills})
		filters["name"] = ["in", matching]

	rows, total = repository.list_projects(filters, order_by, page, page_size, repository.text_search(q, ["title"]))

	return ok(rows, page=page, page_size=page_size, total=total, meta={"q": q, "category": category, "skills": skills})


@frappe.whitelist(allow_guest=True)
def get_project(slug: str):
	return ok(repository.get_project_by_slug(slug))
