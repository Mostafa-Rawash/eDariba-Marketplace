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


class TestProposalGuards(unittest.TestCase):
	def _doc(self, **overrides):
		data = {
			"doctype": "Marketplace Proposal",
			"project": "prj-01",
			"freelancer": "acc-01",
			"proposed_amount": 1000,
			"currency": "ج.م",
			"cover_letter": "x" * 100,
		}
		data.update(overrides)
		return frappe.get_doc(data)

	def _with_project(self, status, deadline):
		original = frappe.db.get_value
		frappe.db.get_value = lambda *a, **k: frappe._dict(publication_status=status, deadline=deadline)
		return original

	def test_rejects_proposal_on_closed_or_expired_project(self):
		for status, deadline in (("Closed", "2099-01-01"), ("Draft", "2099-01-01"), ("Published", "2000-01-01")):
			original = self._with_project(status, deadline)
			try:
				with self.assertRaises(frappe.ValidationError):
					self._doc()._guard_project_open()
			finally:
				frappe.db.get_value = original

	def test_accepts_open_project(self):
		original = self._with_project("Published", "2099-01-01")
		try:
			self._doc()._guard_project_open()
		finally:
			frappe.db.get_value = original

	def test_cover_letter_bounds(self):
		with self.assertRaises(frappe.ValidationError):
			self._doc(cover_letter="<p>قصير</p>")._guard_cover_letter()
		self._doc(cover_letter="<p>" + "ن" * 120 + "</p>")._guard_cover_letter()

	def test_status_cannot_change_outside_the_proposal_api(self):
		doc = self._doc(status="Accepted")
		before = frappe.get_doc({**doc.as_dict(), "status": "Submitted"})
		doc.get_doc_before_save = lambda: before
		original = frappe.get_roles
		frappe.get_roles = lambda *a, **k: ["Invoicing Owner"]
		try:
			with self.assertRaises(frappe.PermissionError):
				doc._guard_status_change()
			doc.flags.status_via_api = True
			doc._guard_status_change()
		finally:
			frappe.get_roles = original

	def test_status_time_is_set_once(self):
		doc = self._doc(status="Accepted", accepted_at="2026-01-01 10:00:00")
		before = frappe.get_doc({**doc.as_dict(), "status": "Submitted"})
		doc.get_doc_before_save = lambda: before
		doc.is_new = lambda: False
		doc._stamp_status_time()
		self.assertEqual(str(doc.accepted_at), "2026-01-01 10:00:00")
