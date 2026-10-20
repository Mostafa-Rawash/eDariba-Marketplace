import frappe
import unittest

from edariba_marketplace.marketplace.permissions import has_inquiry_permission


class TestMarketplaceInquiry(unittest.TestCase):
	def _doc(self, **overrides):
		values = {
			"doctype": "Marketplace Inquiry",
			"recipient": "acc-01",
			"requester": "Administrator",
			"requester_name": "Test",
			"requester_email": "test@example.com",
			"requester_phone": "0100000000",
			"details": "x",
		}
		values.update(overrides)
		return frappe.get_doc(values)

	def test_invalid_email_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._doc(requester_email="not-an-email").validate()

	def test_requester_required(self):
		with self.assertRaises(frappe.ValidationError):
			self._doc(requester=None).validate()

	def test_guest_cannot_create(self):
		# S1: requests are created only through api/workspace.submit_request.
		self.assertFalse(has_inquiry_permission(self._doc(), user="Guest", permission_type="create"))
