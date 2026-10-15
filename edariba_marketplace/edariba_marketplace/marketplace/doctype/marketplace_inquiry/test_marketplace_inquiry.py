import frappe
import unittest


class TestMarketplaceInquiry(unittest.TestCase):
	def test_invalid_email_rejected(self):
		doc = frappe.get_doc(
			{
				"doctype": "Marketplace Inquiry",
				"recipient": "acc-01",
				"requester_name": "Test",
				"requester_email": "not-an-email",
				"requester_phone": "0100000000",
				"details": "x",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			doc.validate()
