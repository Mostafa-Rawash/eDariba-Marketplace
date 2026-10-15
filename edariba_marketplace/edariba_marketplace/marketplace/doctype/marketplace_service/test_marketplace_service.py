import frappe
import unittest


class TestMarketplaceService(unittest.TestCase):
	def test_blank_slug_is_rejected(self):
		doc = frappe.get_doc(
			{
				"doctype": "Marketplace Service",
				"title": "Bookkeeping",
				"slug": "   ",
				"provider": "acc-01",
				"category": "bookkeeping",
				"price": 100,
				"currency": "ج.م",
				"price_unit": "Total",
				"description": "x",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			doc.validate()
