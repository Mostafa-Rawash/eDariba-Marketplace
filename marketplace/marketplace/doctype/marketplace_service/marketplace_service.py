import frappe
from frappe import _
from frappe.utils import now_datetime

from marketplace.marketplace.privacy import IdentityMaskedDocument
from marketplace.shared.permissions import can_edit_any


class MarketplaceService(IdentityMaskedDocument):
	def validate(self):
		self.slug = (self.slug or "").strip().lower()
		if not self.slug:
			frappe.throw(_("Slug is required."))

		self._guard_ownership()
		self._guard_publish_transition()

	def _guard_ownership(self):
		"""A provider may only publish services under their own profile."""
		if can_edit_any():
			return
		owner_user = frappe.db.get_value("Marketplace Profile", self.provider, "user")
		if owner_user and owner_user != frappe.session.user:
			frappe.throw(_("You can only manage services under your own profile."))

	def _guard_publish_transition(self):
		if not self.has_value_changed("publication_status"):
			return
		if self.publication_status == "Published":
			if not (self.title and self.description):
				frappe.throw(_("Title and description are required before publishing."))
			if not frappe.db.get_value("Marketplace Profile", self.provider, "offers_services"):
				frappe.throw(_("Turn on 'Offers Services' on the profile before publishing a service."))
			self.published_at = now_datetime()
