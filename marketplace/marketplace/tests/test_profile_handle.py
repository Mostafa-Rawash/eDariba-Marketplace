import unittest

import frappe

from marketplace.marketplace import profile_handle
from marketplace.marketplace.profile_handle import HANDLE, handle_for, previous_slugs

OWNER = "test_handle_owner@example.com"
OTHER = "test_handle_other@example.com"


class TestHandleRules(unittest.TestCase):
	def test_handle_is_lowercased_username_without_at(self):
		self.assertEqual(handle_for(" @Ahmed_Ali "), "ahmed_ali")

	def test_url_safe_characters_only(self):
		self.assertTrue(HANDLE.match("ahmed-ali_2"))
		for bad in ("ah", "ahmed.ali", "أحمد", "a" * 31):
			self.assertFalse(HANDLE.match(bad), bad)

	def test_previous_slugs_parse(self):
		self.assertEqual(previous_slugs("a\n\n b \n"), ["a", "b"])


def _user(email, username):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "Handle", "username": username, "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	return frappe.get_doc("User", email)


def _profile(user, slug):
	if not frappe.db.exists("Marketplace Profile", {"user": user}):
		frappe.get_doc(
			{
				"doctype": "Marketplace Profile",
				"user": user,
				"profile_type": "Individual",
				"display_name": "Handle Test",
				"slug": slug,
				"governorate": "القاهرة",
			}
		).insert(ignore_permissions=True)
	return frappe.db.get_value("Marketplace Profile", {"user": user}, "name")


class TestProfileFollowsUsername(unittest.TestCase):
	def setUp(self):
		self.owner = _user(OWNER, "handle_owner_start")
		_user(OTHER, "handle_other_user")
		self.other_profile = _profile(OTHER, "handle-other-profile")
		self.start = _profile(OWNER, "handle-owner-profile")

	def tearDown(self):
		frappe.db.rollback()

	def test_username_change_renames_profile_and_keeps_old_slug(self):
		self.owner.username = "Handle_Owner_New"
		self.owner.save(ignore_permissions=True)
		new = frappe.db.get_value("Marketplace Profile", {"user": OWNER}, ["name", "slug", "previous_slugs"], as_dict=True)
		self.assertEqual((new.name, new.slug), ("handle_owner_new", "handle_owner_new"))
		self.assertIn(self.start, previous_slugs(new.previous_slugs))
		self.assertEqual(profile_handle.owner_of_slug(self.start), "handle_owner_new")

	def test_cannot_take_another_profiles_slug(self):
		self.owner.username = self.other_profile
		with self.assertRaises(frappe.DuplicateEntryError):
			self.owner.save(ignore_permissions=True)

	def test_unsafe_username_rejected_for_profile_owners(self):
		self.owner.username = "handle.owner"
		with self.assertRaises(frappe.ValidationError):
			self.owner.save(ignore_permissions=True)

	def test_sync_renames_an_older_profile_to_the_username(self):
		# setUp gives the owner username "handle_owner_start" and slug "handle-owner-profile".
		self.assertEqual(profile_handle.sync_my_profile_link(OWNER), "handle_owner_start")
		self.assertEqual(frappe.db.get_value("Marketplace Profile", {"user": OWNER}, "name"), "handle_owner_start")
		# Second call: already matching, nothing to do.
		self.assertEqual(profile_handle.sync_my_profile_link(OWNER), "handle_owner_start")
