"""Who is who in the active office (workspace), loaded from the database.

The rules themselves are in office/rules.py; this module only reads the rows
they need. An office is an `accounting` workspace: the Tenant, its Owner, its
Members and their `allowed_companies`. This module is the only place the office
reads them, read-only, through accounting's own helpers
(accounting/tenant/workspace.py), so the board follows the same workspace and
company rules as the rest of the app. The one thing the marketplace writes on
Member is its own `member_type` custom field (fixtures/custom_field.json,
office/api.py set_member_type).
"""
import frappe
from frappe import _

from marketplace.office import rules

COLUMN = "Office Task Column"
TASK = "Office Task"


def office_context(user=None):
	"""(tenant, role, allowed) for the user's active workspace. `role` is
	rules.OWNER, rules.EMPLOYEE or None; `allowed` is an Employee's companies."""
	from accounting.tenant.workspace import workspace_context

	user = user or frappe.session.user
	tenant, workspace_role, allowed = workspace_context(user)
	member_type = None
	if workspace_role == "member":
		member_type = frappe.db.get_value(
			"Member", {"email": user, "tenant": tenant, "status": "Active"}, "member_type")
	return tenant, rules.office_role(workspace_role, member_type), allowed or []


def require_office(user=None, owner=False):
	"""The office context, or a PermissionError for clients and outsiders (and
	for Employees when `owner` is set)."""
	tenant, role, allowed = office_context(user)
	if not tenant or role is None:
		frappe.throw(_("The task board is for the account owner and their employees"), frappe.PermissionError)
	if owner and role != rules.OWNER:
		frappe.throw(_("Only the account owner can do this"), frappe.PermissionError)
	return tenant, role, allowed


def tenant_owner(tenant):
	return frappe.db.get_value("Tenant", tenant, "user")


def employees(tenant):
	"""{email: [companies they may use]} for the tenant's Active Employees."""
	from accounting.tenant.workspace import parse_allowed

	rows = frappe.get_all(
		"Member",
		filters={"tenant": tenant, "status": "Active", "member_type": rules.MEMBER_EMPLOYEE},
		fields=["email", "allowed_companies"],
	)
	return {row.email: parse_allowed(row.allowed_companies) for row in rows}


def columns(tenant):
	"""The office's columns in display order. Creates the default ones the first
	time an office opens its board."""
	rows = frappe.get_all(
		COLUMN, filters={"tenant": tenant}, fields=["name", "title", "is_done", "column_order"],
		order_by="column_order asc, creation asc")
	if rows:
		return rows
	for position, (title, is_done) in enumerate(rules.DEFAULT_COLUMNS):
		frappe.get_doc({
			"doctype": COLUMN, "tenant": tenant, "title": title, "is_done": is_done, "column_order": position,
		}).insert(ignore_permissions=True)
	return frappe.get_all(
		COLUMN, filters={"tenant": tenant}, fields=["name", "title", "is_done", "column_order"],
		order_by="column_order asc, creation asc")


def can_see(task, user, role, allowed):
	return rules.can_see_task(role, user, allowed, task.get("assignee"), task.get("company"))


def load_task(name, user=None):
	"""The task and the caller's office context. Tasks the caller may not see
	give the same 'not found' as a missing one, so names cannot be probed."""
	user = user or frappe.session.user
	tenant, role, allowed = require_office(user)
	doc = frappe.get_doc(TASK, name) if name and frappe.db.exists(TASK, name) else None
	if doc is None or doc.tenant != tenant or not can_see(doc, user, role, allowed):
		frappe.throw(_("Task not found"), frappe.DoesNotExistError)
	return doc, (tenant, role, allowed)
