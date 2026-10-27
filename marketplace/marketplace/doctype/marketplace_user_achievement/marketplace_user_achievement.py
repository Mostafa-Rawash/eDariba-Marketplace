import frappe
from frappe import _
from frappe.model.document import Document


class MarketplaceUserAchievement(Document):
	def validate(self):
		self.unique_key = f"{self.user}|{self.achievement}"
		if not self.is_new() and (self.has_value_changed("user") or self.has_value_changed("achievement")):
			frappe.throw(_("An achievement record cannot be moved to another user or achievement."))
