import frappe
from frappe.model.document import Document


class MarketplaceSpecialty(Document):
	def validate(self):
		self.title = " ".join((self.title or "").split())
		if not self.title:
			frappe.throw("Title is required.")
