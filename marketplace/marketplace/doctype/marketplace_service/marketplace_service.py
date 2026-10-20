import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from marketplace.marketplace.permissions import is_moderator


class MarketplaceService(Document):
	def validate(self):
		self.slug = (self.slug or "").strip().lower()
		if not self.slug:
			frappe.throw(_("Slug is required."))

		self._guard_ownership()
		self._guard_publish_transition()

	def _guard_ownership(self):
		"""A provider may only publish services under their own profile."""
		if frappe.session.user == "Administrator" or is_moderator():
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
			if not frappe.db.get_value("Marketplace Profile", self.provider, "offers_services"):
				frappe.throw(_("Turn on 'Offers Services' on the profile before publishing a service."))
			self.published_at = now_datetime()
