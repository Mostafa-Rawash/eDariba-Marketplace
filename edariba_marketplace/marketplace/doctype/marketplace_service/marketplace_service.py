import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class MarketplaceService(Document):
	def validate(self):
		self.slug = (self.slug or "").strip().lower()
		if not self.slug:
			frappe.throw(_("Slug is required."))

		self._guard_ownership()
		self._guard_publish_transition()

	def _guard_ownership(self):
		"""A provider may only publish services under their own profile."""
		if frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles():
			return
		owner_user = frappe.db.get_value("Marketplace Profile", self.provider, "user")
		if owner_user and owner_user != frappe.session.user:
			frappe.throw(_("You can only manage services under your own profile."))

	def _guard_publish_transition(self):
		if not self.has_value_changed("publication_status"):
			return
		if self.publication_status == "Published":
			if not (self.title and self.description and self.thumbnail):
				frappe.throw(_("Title, description, and thumbnail are required before publishing."))
			self.published_at = now_datetime()
