import frappe
from frappe import _
from frappe.utils import now_datetime

from marketplace.marketplace import profile_completion, verification
from marketplace.marketplace.privacy import IdentityMaskedDocument
from marketplace.shared.permissions import can_edit_any

# Set only by the server (controller, marketplace/profile_handle.py) or a System Manager.
# An owner's save through /api/resource cannot change them.
PROTECTED_FIELDS = ("user", "slug", "previous_slugs", "verification_method", "verified_at", "published_at")


class MarketplaceProfile(IdentityMaskedDocument):
	def validate(self):
		self.slug = (self.slug or "").strip().lower()
		if not self.slug:
			frappe.throw(_("Slug is required."))

		self._guard_protected_fields()
		self._apply_verification_policy()
		self._guard_publish_transition()
		self._check_specialties()

	def _guard_protected_fields(self):
		if self.is_new() or can_edit_any():
			return
		# Only the owner edits a profile, whatever the permission hooks allowed.
		before = self.get_doc_before_save()
		if before and before.user != frappe.session.user:
			frappe.throw(_("You can only edit your own profile."), frappe.PermissionError)
		changed = [f for f in PROTECTED_FIELDS + ("company",) if self.has_value_changed(f)]
		if changed:
			frappe.throw(_("These fields cannot be changed: {0}").format(", ".join(changed)), frappe.PermissionError)

	def _apply_verification_policy(self):
		"""See marketplace/verification.py: verified by default while verification
		is bypassed; only a System Manager changes the status by hand (support
		cannot; a verifier role comes later)."""
		required = verification.verification_required()
		editor = can_edit_any()
		if self.is_new():
			self.verification_status, self.verification_method = verification.status_for_new_profile(required)
			self.verified_at = now_datetime() if self.verification_status == verification.VERIFIED else None
			return

		if self.has_value_changed("verification_status"):
			previous = self.get_doc_before_save().verification_status
			if editor:
				verified = self.verification_status == verification.VERIFIED
				self.verification_method = verification.MODERATOR if verified else None
				self.verified_at = now_datetime() if verified else None
			elif not verification.owner_may_change(previous, self.verification_status, required):
				frappe.throw(_("Only an administrator can change verification status."), frappe.PermissionError)

		if verification.auto_verify(self.verification_status, required):
			self.verification_status = verification.VERIFIED
			self.verification_method = verification.AUTOMATIC
			self.verified_at = now_datetime()

	def _guard_publish_transition(self):
		if not self.has_value_changed("publication_status"):
			return

		if self.publication_status == "Published":
			if profile_completion.publish_problems(profile_completion.profile_dict(self)):
				frappe.throw(_("Bio, headline, and years of experience are required before publishing."))
			self.published_at = now_datetime()

	def _check_specialties(self):
		"""Specialties are picked from Marketplace Specialty. Only newly added
		ones are checked, so a profile keeps labels it had before the list
		existed (or that were since deactivated) without blocking its saves."""
		seen = set()
		for row in list(self.specialties):
			row.label = " ".join((row.label or "").split())
			if not row.label or row.label in seen:
				self.remove(row)
				continue
			seen.add(row.label)

		before = self.get_doc_before_save()
		kept = {row.label for row in before.specialties} if before else set()
		added = [label for label in seen if label not in kept]
		if not added:
			return
		active = set(
			frappe.get_all(
				"Marketplace Specialty",
				filters={"title": ("in", added), "is_active": 1},
				pluck="title",
				ignore_permissions=True,
			)
		)
		unknown = [label for label in added if label not in active]
		if unknown:
			frappe.throw(_("Choose specialties from the list: {0}").format("، ".join(unknown)))
