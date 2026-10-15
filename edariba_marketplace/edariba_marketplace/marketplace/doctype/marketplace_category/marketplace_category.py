import frappe
from frappe.model.document import Document


class MarketplaceCategory(Document):
	def validate(self):
		self.slug = (self.slug or "").strip().lower()
		if not self.slug:
			frappe.throw("Slug is required.")
