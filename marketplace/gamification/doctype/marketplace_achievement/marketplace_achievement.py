import frappe
from frappe import _
from frappe.model.document import Document

from marketplace.gamification.rules import METRICS


class MarketplaceAchievement(Document):
	def validate(self):
		self.code = (self.code or "").strip().lower()
		if not self.code:
			frappe.throw(_("Code is required."))
		if self.metric not in METRICS:
			frappe.throw(_("Unknown metric."))
		if (self.threshold or 0) < 1:
			frappe.throw(_("Threshold must be at least 1."))
