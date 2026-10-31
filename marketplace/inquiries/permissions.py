"""Row-level permission rules for Marketplace Inquiry (see marketplace/permissions.py
for why both halves are needed). Requests are written only through
inquiries/api.py."""

import frappe

from marketplace.shared.permissions import is_moderator, sees_all


# --------------------------------------------------------------- Inquiry ---

def inquiry_query_conditions(user: str) -> str:
	"""Fully private: visible only to the requester, the recipient provider,
	or moderators. Guests get nothing (no DocPerm at all)."""
	if is_moderator(user):
		return ""
	escaped = frappe.db.escape(user)
	return (
		"(`tabMarketplace Inquiry`.`requester` = {user} OR `tabMarketplace Inquiry`.`recipient` in "
		"(select `name` from `tabMarketplace Profile` where `user` = {user}))"
	).format(user=escaped)


def has_inquiry_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool:
	user = user or frappe.session.user
	if sees_all(user, permission_type):
		return True
	if permission_type == "create":
		# Requests are created only by inquiries/api.submit_request.
		return False
	if doc.requester == user:
		return True
	owner_user = frappe.db.get_value("Marketplace Profile", doc.recipient, "user")
	return owner_user == user
