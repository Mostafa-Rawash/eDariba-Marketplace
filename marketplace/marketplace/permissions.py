"""Row-level permission rules for Marketplace Profile and Service. Inquiry
rules live in inquiries/permissions.py, Project and Proposal in
freelance/permissions.py; all of them follow the pattern described here.

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
through inquiries/api.py and freelance/api.py. Guest has no DocPerm on
Profile, Service or Project since 2026-10-26 (public reads use the modules' public_api),
so the Guest branches below only matter for future DocTypes.
"""

import frappe

from marketplace.shared.permissions import is_moderator, is_read, published_condition, sees_all, stored_value


# ---------------------------------------------------------------- Profile ---

def profile_query_conditions(user: str) -> str:
	if is_moderator(user):
		return ""
	owned = f"`tabMarketplace Profile`.`user` = {frappe.db.escape(user)}"
	return f"({published_condition('tabMarketplace Profile')} OR {owned})"


def has_profile_permission(doc, ptype: str | None = None, user: str | None = None, debug: bool = False) -> bool:
	user = user or frappe.session.user
	if sees_all(user, ptype):
		return True
	if doc.publication_status == "Published" and is_read(ptype):
		return True
	return stored_value(doc, "user", ptype) == user


# ---------------------------------------------------------------- Service ---

def service_query_conditions(user: str) -> str:
	if is_moderator(user):
		return ""
	owned = (
		"`tabMarketplace Service`.`provider` in "
		"(select `name` from `tabMarketplace Profile` where `user` = {user})"
	).format(user=frappe.db.escape(user))
	return f"({published_condition('tabMarketplace Service')} OR {owned})"


def has_service_permission(doc, ptype: str | None = None, user: str | None = None, debug: bool = False) -> bool:
	user = user or frappe.session.user
	if sees_all(user, ptype):
		return True
	if doc.publication_status == "Published" and is_read(ptype):
		return True
	owner_user = frappe.db.get_value("Marketplace Profile", stored_value(doc, "provider", ptype), "user")
	return owner_user == user
