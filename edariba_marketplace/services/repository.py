"""Read-only data access for the three public Marketplace entities.

Every function here filters to publication_status = "Published" explicitly —
it does not rely on the permission_query_conditions hooks (marketplace/permissions.py)
as the only gate, because frappe.get_all(ignore_permissions=True) is used for
the public endpoints (Guests have no session-based row visibility to begin
with) and a missed `ignore_permissions` elsewhere must not silently leak
drafts. Belt and suspenders: both the explicit filter here AND the
permission hooks enforce the same rule independently.
"""

import frappe

from edariba_marketplace.services.serializers import (
	PROFILE_LIST_FIELDS,
	PROJECT_LIST_FIELDS,
	SERVICE_LIST_FIELDS,
	serialize_profile,
	serialize_project,
	serialize_service,
)


def _paginate(filters: dict, doctype: str, fields: list[str], order_by: str, page: int, page_size: int):
	start = (page - 1) * page_size
	rows = frappe.get_all(
		doctype,
		filters=filters,
		fields=fields,
		order_by=order_by,
		limit_start=start,
		limit_page_length=page_size,
		ignore_permissions=True,
	)
	total = frappe.db.count(doctype, filters=filters)
	return rows, total


def _attach_tag_field(rows: list, parent_doctype: str, tag_fieldname: str, out_key: str) -> None:
	"""Bulk-fetch a Marketplace Tag child table for a page of list rows and
	attach it as `out_key` on each row — one grouped query for the whole
	page, not one query per row. Several list-view cards render this
	unconditionally with no `?? []` fallback (card-accountant.php's
	specialties, card-project.php's required_skills), so leaving it out of
	a list response is not a cosmetic gap — it's a fatal TypeError in
	array_slice() on the WordPress side once real Frappe data is wired in."""
	if not rows:
		return
	names = [r["name"] for r in rows]
	child_rows = frappe.get_all(
		"Marketplace Tag",
		filters={"parenttype": parent_doctype, "parentfield": tag_fieldname, "parent": ["in", names]},
		fields=["parent", "label"],
		order_by="idx asc",
		ignore_permissions=True,
	)
	by_parent: dict[str, list[str]] = {}
	for child in child_rows:
		by_parent.setdefault(child["parent"], []).append(child["label"])
	for row in rows:
		row[out_key] = by_parent.get(row["name"], [])


# --------------------------------------------------------------- Profiles ---

def list_profiles(filters: dict, order_by: str, page: int, page_size: int):
	filters = {**filters, "publication_status": "Published"}
	rows, total = _paginate(filters, "Marketplace Profile", PROFILE_LIST_FIELDS, order_by, page, page_size)
	_attach_tag_field(rows, "Marketplace Profile", "specialties", "specialties")
	return rows, total


def get_profile_by_slug(slug: str):
	name = frappe.db.get_value(
		"Marketplace Profile", {"slug": slug, "publication_status": "Published"}, "name"
	)
	if not name:
		frappe.throw("Profile not found.", frappe.DoesNotExistError)
	doc = frappe.get_doc("Marketplace Profile", name)
	return serialize_profile(doc, detail=True)


def published_services_for_provider(provider_name: str, limit: int = 20):
	"""Feeds the accountant-profile.php service cards, which render
	description and features unconditionally (no `?? []`/`?? ''` fallback)
	— richer than the generic catalog list card, so this pulls "description"
	on top of SERVICE_LIST_FIELDS and attaches "features" too."""
	rows = frappe.get_all(
		"Marketplace Service",
		filters={"provider": provider_name, "publication_status": "Published"},
		fields=SERVICE_LIST_FIELDS + ["description"],
		limit_page_length=limit,
		ignore_permissions=True,
	)
	_attach_tag_field(rows, "Marketplace Service", "features", "features")
	return rows


# ---------------------------------------------------------------- Services ---

def list_services(filters: dict, order_by: str, page: int, page_size: int):
	filters = {**filters, "publication_status": "Published"}
	rows, total = _paginate(filters, "Marketplace Service", SERVICE_LIST_FIELDS, order_by, page, page_size)
	_attach_tag_field(rows, "Marketplace Service", "badges", "badges")
	_attach_tag_field(rows, "Marketplace Service", "features", "features")
	return rows, total


def get_service_by_slug(slug: str):
	name = frappe.db.get_value(
		"Marketplace Service", {"slug": slug, "publication_status": "Published"}, "name"
	)
	if not name:
		frappe.throw("Service not found.", frappe.DoesNotExistError)
	doc = frappe.get_doc("Marketplace Service", name)
	return serialize_service(doc, detail=True)


# ---------------------------------------------------------------- Projects ---

def list_projects(filters: dict, order_by: str, page: int, page_size: int):
	filters = {**filters, "publication_status": "Published"}
	rows, total = _paginate(filters, "Marketplace Project", PROJECT_LIST_FIELDS, order_by, page, page_size)
	_attach_tag_field(rows, "Marketplace Project", "required_skills", "required_skills")
	return rows, total


def get_project_by_slug(slug: str):
	name = frappe.db.get_value(
		"Marketplace Project", {"slug": slug, "publication_status": "Published"}, "name"
	)
	if not name:
		frappe.throw("Project not found.", frappe.DoesNotExistError)
	doc = frappe.get_doc("Marketplace Project", name)
	return serialize_project(doc, detail=True)
