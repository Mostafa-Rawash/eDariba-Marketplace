""""eDariba partner" badge: a profile whose owner holds an active Partner
(reseller) plan in the accounting app (decision J4 = C, 2026-10-20).

This is the only place the marketplace reads accounting data, and it only
reads: it calls accounting's own helpers instead of querying its tables, so
the rule for "active reseller plan" stays defined in one place. Any failure
(accounting not installed, a renamed helper, a DB error) means "no badge",
never a broken directory page.
"""

import frappe


def is_partner(user: str | None) -> bool:
	if not user:
		return False
	try:
		from accounting.tenant.workspace import own_tenant
		from accounting.tenant.workspace_api import has_active_reseller_plan
	except ImportError:
		return False
	try:
		return bool(has_active_reseller_plan(own_tenant(user)))
	except Exception:
		frappe.log_error(title="Marketplace partner badge lookup failed", message=frappe.get_traceback())
		return False


def partner_users(users: list[str]) -> set[str]:
	"""The subset of `users` that get the badge, for a page of list rows."""
	return {u for u in set(users) if is_partner(u)}
