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
READ_PERMISSION_TYPES = (None, "read", "print", "export", "report")


def is_moderator(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return bool(MODERATOR_ROLES & set(frappe.get_roles(user)))


def can_edit_any(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return user == "Administrator" or bool(EDITOR_ROLES & set(frappe.get_roles(user)))


def sees_all(user: str, permission_type: str | None) -> bool:
	"""For has_permission hooks: staff pass for reading any record; only
	can_edit_any passes for writing one."""
	if can_edit_any(user):
		return True
	return permission_type in READ_PERMISSION_TYPES and is_moderator(user)


def published_condition(doctype_table_alias: str = "") -> str:
	prefix = f"`{doctype_table_alias}`." if doctype_table_alias else ""
	return f"{prefix}`publication_status` = 'Published'"
