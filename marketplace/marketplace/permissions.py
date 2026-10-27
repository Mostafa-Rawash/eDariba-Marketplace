"""Row-level permission rules for the Marketplace DocTypes.

Ownership here is modeled through explicit Link fields (Marketplace
Profile.user, Marketplace Service.provider -> Profile.user,
Marketplace Project.client), not Frappe's built-in `owner` metadata field, so
`if_owner` DocPerm flags cannot express these rules. Both halves are required:

- `permission_query_conditions` scopes *list views and reports* (SQL WHERE).
- `has_permission` scopes a *single document* fetch/save (frappe.has_permission).

Public/Guest reads are restricted to publication_status = "Published" in both
halves — the query condition keeps unpublished rows out of list results, and
has_permission blocks a guest from loading an unpublished doc by guessing its
name directly.

These hooks only ever narrow what a DocPerm already allows. The app's users
hold "Invoicing Owner", which has DocPerms on Profile, Service and Project
(commit e6a950a) and create-only on Proposal; these hooks and the controllers
keep them to their own records. Requests and proposal status changes go
through api/workspace.py and api/proposals.py. Guest has no DocPerm on
Profile, Service or Project since 2026-10-26 (public reads use api/public/*),
so the Guest branches below only matter for future DocTypes.
"""

import frappe

MODERATOR_ROLES = {"System Manager", "Marketplace Moderator"}


def is_moderator(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return bool(MODERATOR_ROLES & set(frappe.get_roles(user)))


def _published_condition(doctype_table_alias: str = "") -> str:
	prefix = f"`{doctype_table_alias}`." if doctype_table_alias else ""
	return f"{prefix}`publication_status` = 'Published'"


# ---------------------------------------------------------------- Profile ---

def profile_query_conditions(user: str) -> str:
	if is_moderator(user):
		return ""
	owned = f"`tabMarketplace Profile`.`user` = {frappe.db.escape(user)}"
	return f"({_published_condition('tabMarketplace Profile')} OR {owned})"


def has_profile_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool:
	user = user or frappe.session.user
	if is_moderator(user):
		return True
	if doc.publication_status == "Published" and permission_type in (None, "read"):
		return True
	return doc.user == user


# ---------------------------------------------------------------- Service ---

def service_query_conditions(user: str) -> str:
	if is_moderator(user):
		return ""
	owned = (
		"`tabMarketplace Service`.`provider` in "
		"(select `name` from `tabMarketplace Profile` where `user` = {user})"
	).format(user=frappe.db.escape(user))
	return f"({_published_condition('tabMarketplace Service')} OR {owned})"


def has_service_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool:
	user = user or frappe.session.user
	if is_moderator(user):
		return True
	if doc.publication_status == "Published" and permission_type in (None, "read"):
		return True
	owner_user = frappe.db.get_value("Marketplace Profile", doc.provider, "user")
	return owner_user == user


# ---------------------------------------------------------------- Project ---

def project_query_conditions(user: str) -> str:
	if is_moderator(user):
		return ""
	owned = f"`tabMarketplace Project`.`client` = {frappe.db.escape(user)}"
	return f"({_published_condition('tabMarketplace Project')} OR {owned})"


def has_project_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool:
	user = user or frappe.session.user
	if is_moderator(user):
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
	if is_moderator(user):
		return True
	if doc.submitted_by == user:
		return True
	project_client = frappe.db.get_value("Marketplace Project", doc.project, "client")
	return project_client == user


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
	if is_moderator(user):
		return True
	if permission_type == "create":
		# Requests are created only by api/workspace.submit_request.
		return False
	if doc.requester == user:
		return True
	owner_user = frappe.db.get_value("Marketplace Profile", doc.recipient, "user")
	return owner_user == user
