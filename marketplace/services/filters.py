"""Allowlisted filter/sort validation shared by all three listing endpoints.

Nothing here accepts an arbitrary client-supplied field name — every public
filter maps to one specific, known-safe DocType field.
"""

import frappe

ACCOUNTANT_SORT_FIELDS = {
	"experience_years": "experience_years",
	"display_name": "display_name",
}
SERVICE_SORT_FIELDS = {
	"price": "price",
	"title": "title",
}
PROJECT_SORT_FIELDS = {
	"budget_min": "budget_min",
	"deadline": "deadline",
}
SORT_ORDERS = {"asc", "desc"}


def resolve_sort(sort_by: str | None, sort_order: str | None, allowed: dict[str, str], default_field: str) -> str:
	field = allowed.get(sort_by or "", allowed[default_field])
	order = (sort_order or "desc").lower()
	if order not in SORT_ORDERS:
		order = "desc"
	return f"{field} {order}"


def clamp_page_size(page_size: int | str | None, default: int = 20, maximum: int = 50) -> int:
	try:
		value = int(page_size or default)
	except (TypeError, ValueError):
		value = default
	return max(1, min(value, maximum))


def clamp_page(page: int | str | None) -> int:
	try:
		value = int(page or 1)
	except (TypeError, ValueError):
		value = 1
	return max(1, value)


def validate_price_range(min_value, max_value):
	if min_value is not None and max_value is not None and float(max_value) < float(min_value):
		frappe.throw("max value cannot be less than min value.")


def names_matching_tag(parent_doctype: str, tag_fieldname: str, text: str) -> list[str]:
	"""Free-text match against a Marketplace Tag child table (e.g.
	Project.required_skills, Profile.specialties). Mirrors the plain-text
	'skill' input already used in filter-sidebar.php — there is no
	controlled skill/specialty taxonomy in the current product, so this
	does a LIKE match rather than an exact Link lookup. Not indexed; fine
	at current data volume, call out if this ever needs to scale."""
	if not text:
		return []
	rows = frappe.db.sql(
		"""
		select distinct parent from `tabMarketplace Tag`
		where parenttype = %s and parentfield = %s and label like %s
		""",
		(parent_doctype, tag_fieldname, f"%{text}%"),
		as_dict=False,
	)
	return [r[0] for r in rows]
