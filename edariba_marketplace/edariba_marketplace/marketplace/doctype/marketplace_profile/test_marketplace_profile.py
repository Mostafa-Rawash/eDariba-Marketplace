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
	def test_new_profile_defaults_to_pending(self):
		doc = _profile()
		doc.validate()
		self.assertEqual(doc.verification_status, "Pending")

	def test_new_profile_cannot_claim_verified(self):
		doc = _profile(verification_status="Verified")
		with self.assertRaises(frappe.ValidationError):
			doc.validate()

	def test_cannot_publish_without_verification(self):
		doc = _profile()
		doc.verification_status = "Pending"
		doc.publication_status = "Published"
		# simulate "not new" so the publish-transition guard runs
		doc.get_doc_before_save = lambda: frappe.get_doc(
			{**doc.as_dict(), "publication_status": "Draft"}
		)
		with self.assertRaises(frappe.ValidationError):
			doc._guard_publish_transition()
