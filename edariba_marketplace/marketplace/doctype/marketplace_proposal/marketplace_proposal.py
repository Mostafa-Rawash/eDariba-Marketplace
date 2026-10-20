import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

ACTIVE_STATUSES = {"Submitted", "Shortlisted"}


class MarketplaceProposal(Document):
	def validate(self):
		self._guard_submitter_matches_freelancer()
		self._guard_not_own_project()
		self._guard_duplicate_active_proposal()
		if self.is_new():
			self.submitted_at = now_datetime()
			self.status = "Submitted"

	def _guard_submitter_matches_freelancer(self):
		owner_user = frappe.db.get_value("Marketplace Profile", self.freelancer, "user")
		self.submitted_by = frappe.session.user if self.is_new() else self.submitted_by
		if owner_user and self.submitted_by and owner_user != self.submitted_by:
			frappe.throw(_("You can only submit proposals from your own profile."))

	def _guard_not_own_project(self):
		project_client = frappe.db.get_value("Marketplace Project", self.project, "client")
		if project_client and self.submitted_by and project_client == self.submitted_by:
			frappe.throw(_("You cannot submit a proposal to your own project."))

	def _guard_duplicate_active_proposal(self):
		if not self.is_new():
			return
		existing = frappe.db.exists(
			"Marketplace Proposal",
			{
				"project": self.project,
				"freelancer": self.freelancer,
				"status": ["in", list(ACTIVE_STATUSES)],
			},
		)
		if existing:
			frappe.throw(_("You already have an active proposal on this project."))
