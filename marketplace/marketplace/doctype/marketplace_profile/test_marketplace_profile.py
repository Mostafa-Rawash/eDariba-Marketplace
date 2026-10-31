import frappe
import unittest


def _profile(**overrides):
	data = {
		"doctype": "Marketplace Profile",
		"user": "test_profile_owner@example.com",
		"profile_type": "Individual",
		"display_name": "Test Accountant",
		"slug": "test-accountant",
		"headline": "Tax Consultant",
		"governorate": "القاهرة",
		"experience_years": 5,
		"bio": "Bio text.",
	}
	data.update(overrides)
	return frappe.get_doc(data)


class TestMarketplaceProfile(unittest.TestCase):
	# Verification is bypassed (marketplace/verification.py): verified by default.
	def test_new_profile_is_verified_automatically(self):
		doc = _profile()
		doc.validate()
		self.assertEqual((doc.verification_status, doc.verification_method), ("Verified", "Automatic"))
		self.assertTrue(doc.verified_at)

	def test_new_profile_status_ignores_what_the_client_sent(self):
		for sent in ("Pending", "Rejected", "Verified"):
			doc = _profile(verification_status=sent, verification_method="Moderator")
			doc.validate()
			self.assertEqual((doc.verification_status, doc.verification_method), ("Verified", "Automatic"), sent)

	def test_new_profile_is_pending_when_verification_is_required(self):
		frappe.local.conf["marketplace_verification_required"] = 1
		try:
			doc = _profile()
			doc.validate()
			self.assertEqual(doc.verification_status, "Pending")
		finally:
			frappe.local.conf.pop("marketplace_verification_required", None)

	def test_owner_cannot_change_verification_or_protected_fields(self):
		doc = _profile()
		before = frappe.get_doc(doc.as_dict())
		doc.get_doc_before_save = lambda: before
		doc.is_new = lambda: False
		original = frappe.get_roles
		frappe.get_roles = lambda *a, **k: ["Invoicing Owner"]
		try:
			doc.verification_status = "Rejected"
			with self.assertRaises(frappe.PermissionError):
				doc._apply_verification_policy()
			doc.verification_status = before.verification_status
			for field, value in (("user", "someone@example.com"), ("slug", "taken"), ("verified_at", "2020-01-01")):
				doc.set(field, value)
				with self.assertRaises(frappe.PermissionError):
					doc._guard_protected_fields()
				doc.set(field, before.get(field))
		finally:
			frappe.get_roles = original

	def test_pending_profile_is_verified_on_save(self):
		doc = _profile(verification_status="Pending")
		before = frappe.get_doc(doc.as_dict())
		doc.get_doc_before_save = lambda: before
		doc.is_new = lambda: False
		doc._apply_verification_policy()
		self.assertEqual((doc.verification_status, doc.verification_method), ("Verified", "Automatic"))

	def test_rejected_profile_stays_rejected(self):
		doc = _profile(verification_status="Rejected")
		before = frappe.get_doc(doc.as_dict())
		doc.get_doc_before_save = lambda: before
		doc.is_new = lambda: False
		doc._apply_verification_policy()
		self.assertEqual(doc.verification_status, "Rejected")

	def test_can_publish_without_verification(self):
		# The owner publishes their own profile; verification does not gate it.
		doc = _profile()
		doc.verification_status = "Pending"
		doc.publication_status = "Published"
		# simulate "not new" so the publish-transition guard runs
		doc.get_doc_before_save = lambda: frappe.get_doc(
			{**doc.as_dict(), "publication_status": "Draft"}
		)
		doc._guard_publish_transition()
		self.assertTrue(doc.published_at)

	def test_cannot_publish_without_bio(self):
		doc = _profile(bio="")
		doc.publication_status = "Published"
		doc.get_doc_before_save = lambda: frappe.get_doc(
			{**doc.as_dict(), "publication_status": "Draft"}
		)
		with self.assertRaises(frappe.ValidationError):
			doc._guard_publish_transition()


LISTED = "تخصص اختبار مدرج"


class TestProfileSpecialties(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		if not frappe.db.exists("Marketplace Specialty", LISTED):
			frappe.get_doc({"doctype": "Marketplace Specialty", "title": LISTED}).insert(ignore_permissions=True)

	def test_unlisted_specialty_is_rejected(self):
		doc = _profile(specialties=[{"label": "تخصص غير مدرج"}])
		with self.assertRaises(frappe.ValidationError):
			doc.validate()

	def test_listed_specialty_is_cleaned_and_deduplicated(self):
		doc = _profile(specialties=[{"label": f"  {LISTED} "}, {"label": LISTED}])
		doc.validate()
		self.assertEqual([row.label for row in doc.specialties], [LISTED])

	def test_label_saved_before_the_list_is_kept(self):
		# Profiles created before Marketplace Specialty keep their free-text labels.
		doc = _profile(specialties=[{"label": "تخصص قديم"}])
		doc.get_doc_before_save = lambda: frappe.get_doc(doc.as_dict())
		doc._check_specialties()
		self.assertEqual([row.label for row in doc.specialties], ["تخصص قديم"])
