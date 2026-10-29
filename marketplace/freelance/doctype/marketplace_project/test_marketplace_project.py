import frappe
import unittest


def _project(**overrides):
	data = {
		"doctype": "Marketplace Project",
		"title": "Test Project",
		"slug": "test-project",
		"category": "tax",
		"client": "test_client@example.com",
		"client_display_name": "Test Client",
		"client_type": "شركة ناشئة",
		"description": "Brief",
		"budget_min": 1000,
		"budget_max": 2000,
		"currency": "ج.م",
		"deadline": "2099-01-01",
	}
	data.update(overrides)
	return frappe.get_doc(data)


class TestMarketplaceProject(unittest.TestCase):
	def test_budget_max_below_min_is_rejected(self):
		doc = _project(budget_min=2000, budget_max=1000)
		with self.assertRaises(frappe.ValidationError):
			doc._guard_budget()

	def test_past_deadline_rejected_on_new_doc(self):
		doc = _project(deadline="2000-01-01")
		with self.assertRaises(frappe.ValidationError):
			doc._guard_deadline()
