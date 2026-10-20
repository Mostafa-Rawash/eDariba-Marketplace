import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

MODERATOR_ROLES = {"System Manager", "Marketplace Moderator"}


def _is_moderator(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return bool(MODERATOR_ROLES & set(frappe.get_roles(user)))


class MarketplaceProfile(Document):
	def validate(self):
		self.slug = (self.slug or "").strip().lower()
		if not self.slug:
			frappe.throw(_("Slug is required."))

		self._guard_moderation_fields()
		self._guard_publish_transition()

	def _guard_moderation_fields(self):
		"""verification_status is a moderation decision, not something the
		profile owner can set on themselves — mirrors the task rule that a
		professional cannot change their own verification outcome."""
		if self.is_new():
			if self.verification_status and self.verification_status != "Pending":
				frappe.throw(_("New profiles always start as Pending verification."))
			return

		if self.has_value_changed("verification_status") and not _is_moderator():
			frappe.throw(_("Only a moderator can change verification status."))

	def _guard_publish_transition(self):
		if not self.has_value_changed("publication_status"):
			return

		if self.publication_status == "Published":
			if self.verification_status != "Verified":
				frappe.throw(_("Only a verified profile can be published."))
			if not (self.bio and self.headline and self.experience_years is not None):
				frappe.throw(_("Bio, headline, and years of experience are required before publishing."))
			self.published_at = now_datetime()
