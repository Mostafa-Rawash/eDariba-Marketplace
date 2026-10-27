import frappe
from frappe import _
from frappe.model.document import Document


class MarketplacePointsEntry(Document):
	"""Append-only: see services/gamification.py."""

	def validate(self):
		if not self.is_new():
			frappe.throw(_("Points entries cannot be changed. Add a correcting entry instead."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("Points entries cannot be deleted. Add a correcting entry instead."), frappe.PermissionError)
