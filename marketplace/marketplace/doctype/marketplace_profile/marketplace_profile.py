import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from marketplace.marketplace.permissions import is_moderator


class MarketplaceProfile(Document):
	def validate(self):
		self.slug = (self.slug or "").strip().lower()
		if not self.slug:
			frappe.throw(_("Slug is required."))

		self._guard_moderation_fields()
		self._guard_publish_transition()

	def _guard_moderation_fields(self):
		"""The owner activates their own profile: Pending (not active) <->
		Verified (active). Rejected stays a moderator decision; the owner can
		only send a rejected profile back to Pending."""
		if self.is_new():
			if self.verification_status and self.verification_status != "Pending":
				frappe.throw(_("New profiles always start as Pending verification."))
			return

		if not self.has_value_changed("verification_status") or is_moderator():
			return
		previous = (self.get_doc_before_save() or {}).get("verification_status")
		owner = self.user == frappe.session.user
		allowed = (previous, self.verification_status) in (
			("Pending", "Verified"),
			("Verified", "Pending"),
			("Rejected", "Pending"),
		)
		if not (owner and allowed):
			frappe.throw(_("Only a moderator can change verification status."))

	def _guard_publish_transition(self):
		if not self.has_value_changed("publication_status"):
			return

		if self.publication_status == "Published":
			if not (self.bio and self.headline and self.experience_years is not None):
				frappe.throw(_("Bio, headline, and years of experience are required before publishing."))
			self.published_at = now_datetime()
