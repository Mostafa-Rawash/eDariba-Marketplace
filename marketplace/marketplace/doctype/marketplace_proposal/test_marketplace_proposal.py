import frappe
import unittest


class TestMarketplaceProposal(unittest.TestCase):
	def test_rejects_proposal_on_own_project(self):
		doc = frappe.get_doc(
			{
				"doctype": "Marketplace Proposal",
				"project": "prj-01",
				"freelancer": "acc-01",
				"submitted_by": "same_user@example.com",
				"proposed_amount": 1000,
				"currency": "ج.م",
				"cover_letter": "x",
			}
		)
		doc.submitted_by = "same_user@example.com"
		# simulate frappe.db.get_value("Marketplace Project", ..., "client") == submitted_by
		original = frappe.db.get_value
		frappe.db.get_value = lambda *a, **k: "same_user@example.com"
		try:
			with self.assertRaises(frappe.ValidationError):
				doc._guard_not_own_project()
		finally:
			frappe.db.get_value = original
