import frappe
import unittest


class TestMarketplaceCategory(unittest.TestCase):
	def test_slug_is_lowercased(self):
		doc = frappe.get_doc(
			{
				"doctype": "Marketplace Category",
				"title": "Bookkeeping",
				"slug": "Bookkeeping",
			}
		)
		doc.validate()
		self.assertEqual(doc.slug, "bookkeeping")

	def test_blank_slug_is_rejected(self):
		doc = frappe.get_doc({"doctype": "Marketplace Category", "title": "X", "slug": "   "})
		with self.assertRaises(frappe.ValidationError):
			doc.validate()
