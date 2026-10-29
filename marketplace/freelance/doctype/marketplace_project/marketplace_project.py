import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, today

from marketplace.marketplace.privacy import IdentityMaskedDocument
from marketplace.shared.permissions import can_edit_any


class MarketplaceProject(IdentityMaskedDocument):
	def validate(self):
		self.slug = (self.slug or "").strip().lower()
		if not self.slug:
			frappe.throw(_("Slug is required."))

		self._guard_ownership()
		self._guard_hire_fields()
		self._guard_budget()
		self._guard_deadline()
		self._guard_publish_transition()
		if self.publication_status == "Closed" and not self.closed_at:
			self.closed_at = now_datetime()

	def _guard_hire_fields(self):
		"""accepted_proposal and closed_at are set by the server
		(freelance/api.py, the line above), never by the client's own save.
		support_via_api: freelance/api.py support_close_project."""
		if self.is_new() or self.flags.hire_via_api or self.flags.support_via_api or can_edit_any():
			return
		if self.has_value_changed("accepted_proposal") or self.has_value_changed("closed_at"):
			frappe.throw(_("These fields cannot be changed: accepted_proposal, closed_at"), frappe.PermissionError)

	def _guard_ownership(self):
		if self.flags.support_via_api or can_edit_any():
			return
		if self.client and self.client != frappe.session.user:
			frappe.throw(_("You can only manage your own projects."))

	def _guard_budget(self):
		if self.budget_min is not None and self.budget_max is not None and self.budget_max < self.budget_min:
			frappe.throw(_("Budget max cannot be less than budget min."))

	def _guard_deadline(self):
		if self.is_new() and self.deadline and getdate(self.deadline) < getdate(today()):
			frappe.throw(_("Deadline cannot be in the past."))

	def _guard_publish_transition(self):
		if not self.has_value_changed("publication_status"):
			return
		if self.publication_status == "Published":
			if not (self.title and self.description and self.budget_min is not None):
				frappe.throw(_("Title, description, and budget are required before publishing."))
			self.published_at = now_datetime()
