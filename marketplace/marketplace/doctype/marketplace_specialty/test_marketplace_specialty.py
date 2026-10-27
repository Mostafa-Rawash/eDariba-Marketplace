import frappe
import unittest


class TestMarketplaceSpecialty(unittest.TestCase):
	def test_title_spaces_are_collapsed(self):
		doc = frappe.get_doc({"doctype": "Marketplace Specialty", "title": "  فحص   ضريبي "})
		doc.validate()
		self.assertEqual(doc.title, "فحص ضريبي")

	def test_blank_title_is_rejected(self):
		doc = frappe.get_doc({"doctype": "Marketplace Specialty", "title": "   "})
		with self.assertRaises(frappe.ValidationError):
			doc.validate()
