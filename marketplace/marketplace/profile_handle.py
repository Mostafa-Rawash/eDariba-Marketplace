"""The public profile link follows the owner's username.

edariba.com/marketplace/accountants/<slug> uses the profile's slug, which is
also its document name. When the owner changes their account username (from
the app's account page or the marketplace profile page, both save
User.username), the profile is renamed to the lowercased username: Frappe's
rename updates every Link to it (services, requests, proposals). The old slug
is kept in previous_slugs so old links still resolve and the WordPress site can
redirect them to the new one.

Wired as User doc_events in hooks.py:
  validate  -> check_username   rejects a username whose handle is taken or not URL-safe
  on_update -> sync_profile_handle
"""

import re

import frappe
from frappe import _

PROFILE = "Marketplace Profile"
# Same characters WordPress keeps in a slug (sanitize_title), so links match.
HANDLE = re.compile(r"^[a-z0-9_-]{3,30}$")


def handle_for(username: str | None) -> str:
	return (username or "").strip(" @").lower()


def profile_of(user: str) -> str | None:
	return frappe.db.get_value(PROFILE, {"user": user}, "name")


def previous_slugs(value: str | None) -> list[str]:
	return [line.strip() for line in (value or "").splitlines() if line.strip()]


def owner_of_slug(slug: str) -> str | None:
	"""The profile that has or had `slug`, or None."""
	if frappe.db.exists(PROFILE, slug):
		return slug
	rows = frappe.get_all(
		PROFILE,
		filters={"previous_slugs": ("like", f"%{slug}%")},
		fields=["name", "previous_slugs"],
		ignore_permissions=True,
	)
	for row in rows:
		if slug in previous_slugs(row.previous_slugs):
			return row.name
	return None


def check_username(doc, method=None):
	"""User.validate: only users with a marketplace profile, only when the
	username changes. The handle must be URL-safe and not belong (now or
	before) to another profile."""
	if doc.is_new() or not doc.has_value_changed("username") or not doc.username:
		return
	mine = profile_of(doc.name)
	if mine:
		check_handle_free(mine, doc.username)


def check_handle_free(profile: str, username: str):
	handle = handle_for(username)
	if not HANDLE.match(handle):
		frappe.throw(
			_("Use 3 to 30 English letters, digits, _ or - in your username; it is your public profile link.")
		)
	owner = owner_of_slug(handle)
	if owner and owner != profile:
		frappe.throw(_("Username {0} is already taken.").format(username), frappe.DuplicateEntryError)


def sync_profile_handle(doc, method=None):
	"""User.on_update: rename the user's profile to their new username."""
	if not doc.has_value_changed("username") or not doc.username:
		return
	old = profile_of(doc.name)
	if old:
		rename_profile(old, handle_for(doc.username))


def sync_my_profile_link(user: str) -> str | None:
	"""Rename `user`'s profile to their current username. For profiles whose
	slug predates the link following the username; a no-op when they match.
	Returns the profile's slug."""
	mine = profile_of(user)
	username = frappe.db.get_value("User", user, "username")
	handle = handle_for(username) if username else None
	if not mine or not handle or handle == mine:
		return mine
	check_handle_free(mine, username)
	rename_profile(mine, handle)
	return handle


def rename_profile(old: str, new: str):
	if old == new:
		return
	history = previous_slugs(frappe.db.get_value(PROFILE, old, "previous_slugs"))
	history = [s for s in history if s != new] + [old]
	# Permissions were checked on the User save that triggered this: the owner
	# renames only their own profile. force: the DocType has allow_rename off so
	# nobody renames profiles from the desk by hand.
	frappe.rename_doc(PROFILE, old, new, force=True, ignore_permissions=True, show_alert=False)
	frappe.db.set_value(PROFILE, new, {"slug": new, "previous_slugs": "\n".join(history)}, update_modified=False)

	# Search index: drop the old point, index the new name.
	from marketplace.search import indexing_service

	indexing_service.on_profile_delete(frappe._dict(name=old))
	indexing_service.on_profile_update(frappe.get_doc(PROFILE, new))
