"""Row-level permission rules for Marketplace Project and Proposal (see
marketplace/permissions.py for why both halves are needed). Proposal status
changes go through freelance/api.py."""

import frappe

from marketplace.shared.permissions import is_moderator, published_condition, sees_all


# ---------------------------------------------------------------- Project ---

def project_query_conditions(user: str) -> str:
	if is_moderator(user):
		return ""
	owned = f"`tabMarketplace Project`.`client` = {frappe.db.escape(user)}"
	return f"({published_condition('tabMarketplace Project')} OR {owned})"


def has_project_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool:
	user = user or frappe.session.user
	if sees_all(user, permission_type):
		return True
	if doc.publication_status == "Published" and permission_type in (None, "read"):
		return True
	return doc.client == user


# --------------------------------------------------------------- Proposal ---

def proposal_query_conditions(user: str) -> str:
	"""Fully private: visible only to the submitting freelancer or the
	client who owns the related project."""
	if is_moderator(user):
		return ""
	as_freelancer = (
		"`tabMarketplace Proposal`.`submitted_by` = {user}"
	).format(user=frappe.db.escape(user))
	as_client = (
		"`tabMarketplace Proposal`.`project` in "
		"(select `name` from `tabMarketplace Project` where `client` = {user})"
	).format(user=frappe.db.escape(user))
	return f"({as_freelancer} OR {as_client})"


def has_proposal_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool:
	user = user or frappe.session.user
	if sees_all(user, permission_type):
		return True
	if doc.submitted_by == user:
		return True
	project_client = frappe.db.get_value("Marketplace Project", doc.project, "client")
	return project_client == user
