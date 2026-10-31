"""Roles and SQL helpers shared by every module's permission hooks.

Each module keeps the row-level rules for its own DocTypes in its own
permissions.py (marketplace/, inquiries/, freelance/); hooks.py wires them.

Two questions, two helpers (decided 2026-10-29):
- is_moderator: may this user SEE every record? System Manager and
  Marketplace Moderator. The moderator is the sales / customer-support team
  that follows requests and projects.
- can_edit_any: may this user CHANGE records they do not own (listings,
  protected fields, verification)? System Manager only. Support acts on
  requests and projects only through the support_* endpoints, with a reason.
A later verifier role will be added to can_edit_any's verification check.
"""

import frappe

MODERATOR_ROLES = {"System Manager", "Marketplace Moderator"}
EDITOR_ROLES = {"System Manager"}
READ_PERMISSION_TYPES = ("read", "print", "export", "report")


def is_moderator(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return bool(MODERATOR_ROLES & set(frappe.get_roles(user)))


def can_edit_any(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return user == "Administrator" or bool(EDITOR_ROLES & set(frappe.get_roles(user)))


def is_read(ptype: str | None) -> bool:
	"""Frappe calls has_permission hooks as hook(doc=, ptype=, user=, debug=)
	and drops keyword arguments a hook does not declare, so hooks must name the
	argument `ptype`. It defaults to "read" when Frappe is asked without one."""
	return (ptype or "read") in READ_PERMISSION_TYPES


def sees_all(user: str, ptype: str | None) -> bool:
	"""For has_permission hooks: staff pass for reading any record; only
	can_edit_any passes for writing one."""
	if can_edit_any(user):
		return True
	return is_read(ptype) and is_moderator(user)


def stored_value(doc, field: str, ptype: str | None = None):
	"""`field` as saved in the database for an existing record, else as on
	`doc`. Frappe checks write permission on a save after the request's values
	are applied to the document, so ownership must come from the stored row,
	not from the payload. A read checks a document as it was loaded, so it
	needs no query."""
	if is_read(ptype):
		return doc.get(field)
	before = getattr(doc, "_doc_before_save", None)
	if before is not None:
		return before.get(field)
	name = doc.get("name")
	if name:
		row = frappe.db.get_value(doc.doctype, name, [field], as_dict=True)
		if row is not None:
			return row.get(field)
	return doc.get(field)


def published_condition(doctype_table_alias: str = "") -> str:
	prefix = f"`{doctype_table_alias}`." if doctype_table_alias else ""
	return f"{prefix}`publication_status` = 'Published'"
