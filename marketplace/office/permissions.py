"""List filters and doc checks for the office DocTypes (hooks.py).

App users hold no DocPerm on Office Task or Office Task Column; they go through
office/api.py. These hooks keep each office to its own rows anyway, wherever
the rows are read (Desk, /api/resource, reports), as tenant/test_isolation_coverage.py
requires for every DocType with a `company` field. Return True for "no
objection" (Frappe still applies the DocPerms); never None.
"""
import frappe

from marketplace.office import access, rules


def _staff(user):
	return user == "Administrator" or "System Manager" in frappe.get_roles(user)


def task_query(user):
	user = user or frappe.session.user
	if _staff(user):
		return ""
	tenant, role, allowed = access.office_context(user)
	if not tenant or role is None:
		return "( 1 = 0 )"
	condition = "`tabOffice Task`.`tenant` = {}".format(frappe.db.escape(tenant))
	if role == rules.OWNER:
		return "( {} )".format(condition)
	visible = "`tabOffice Task`.`assignee` = {}".format(frappe.db.escape(user))
	if allowed:
		names = ", ".join(frappe.db.escape(name) for name in allowed)
		visible = "( {} or `tabOffice Task`.`company` in ({}) )".format(visible, names)
	return "( {} and {} )".format(condition, visible)


def has_task_permission(doc, ptype=None, user=None, debug=False):
	user = user or frappe.session.user
	if _staff(user):
		return True
	tenant, role, allowed = access.office_context(user)
	if not tenant or role is None or doc.get("tenant") != tenant:
		return False
	if role == rules.OWNER:
		return True
	if ptype not in (None, "read", "print", "export", "report"):
		return False
	return rules.can_see_task(role, user, allowed, doc.get("assignee"), doc.get("company"))


def column_query(user):
	user = user or frappe.session.user
	if _staff(user):
		return ""
	tenant, role, _allowed = access.office_context(user)
	if not tenant or role is None:
		return "( 1 = 0 )"
	return "( `tabOffice Task Column`.`tenant` = {} )".format(frappe.db.escape(tenant))


def has_column_permission(doc, ptype=None, user=None, debug=False):
	user = user or frappe.session.user
	if _staff(user):
		return True
	tenant, role, _allowed = access.office_context(user)
	if not tenant or role is None or doc.get("tenant") != tenant:
		return False
	return role == rules.OWNER or ptype in (None, "read", "print", "export", "report")
