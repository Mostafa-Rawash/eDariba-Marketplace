import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, today

from edariba_marketplace.marketplace.permissions import is_moderator


class MarketplaceProject(Document):
	def validate(self):
		self.slug = (self.slug or "").strip().lower()
		if not self.slug:
			frappe.throw(_("Slug is required."))

		self._guard_ownership()
		self._guard_budget()
		self._guard_deadline()
		self._guard_publish_transition()

	def _guard_ownership(self):
		if frappe.session.user == "Administrator" or is_moderator():
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
