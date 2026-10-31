import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, getdate, now_datetime, today

from marketplace.freelance import rules as proposal_rules
from marketplace.marketplace import profile_completion


class MarketplaceProposal(Document):
	def validate(self):
		if self.is_new():
			# Lock the freelancer's profile row for the rest of the transaction,
			# so two simultaneous submits cannot both pass the duplicate and
			# rate checks below.
			frappe.db.get_value("Marketplace Profile", self.freelancer, "name", for_update=True)
		self._guard_freelancer_accepts_projects()
		self._guard_submitter_matches_freelancer()
		self._guard_not_own_project()
		self._guard_duplicate_active_proposal()
		if self.is_new():
			self._guard_project_open()
			self._guard_cover_letter()
			self._guard_rate_limit()
			self.submitted_at = now_datetime()
			self.status = "Submitted"
		else:
			self._guard_status_change()
		self._stamp_status_time()

	def _guard_freelancer_accepts_projects(self):
		if self.is_new() and not frappe.db.get_value("Marketplace Profile", self.freelancer, "accepts_projects"):
			frappe.throw(_("Turn on 'Accepts Projects' on your profile before sending proposals."))

	def _guard_submitter_matches_freelancer(self):
		owner_user = frappe.db.get_value("Marketplace Profile", self.freelancer, "user")
		if self.is_new():
			self.submitted_by = frappe.session.user
		elif self.has_value_changed("submitted_by") or self.has_value_changed("freelancer"):
			frappe.throw(_("You can only submit proposals from your own profile."))
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
				"status": ["in", list(proposal_rules.ACTIVE_STATUSES)],
			},
		)
		if existing:
			frappe.throw(_("You already have an active proposal on this project."))

	def _guard_project_open(self):
		project = frappe.db.get_value("Marketplace Project", self.project, ["publication_status", "deadline"], as_dict=True)
		deadline = getdate(project.deadline) if project and project.deadline else None
		if not project or not proposal_rules.project_open(project.publication_status, deadline, getdate(today())):
			frappe.throw(_("This project is not open for proposals."))

	def _guard_cover_letter(self):
		if not proposal_rules.cover_letter_ok(profile_completion.plain_text(self.cover_letter)):
			frappe.throw(
				_("The cover letter must be between {0} and {1} characters.").format(
					proposal_rules.COVER_LETTER_MIN, proposal_rules.COVER_LETTER_MAX
				)
			)

	def _guard_rate_limit(self):
		recent = frappe.db.count(
			"Marketplace Proposal",
			{"submitted_by": self.submitted_by, "creation": [">", add_to_date(now_datetime(), hours=-1)]},
		)
		if recent >= proposal_rules.PROPOSALS_PER_HOUR:
			frappe.throw(_("You have sent too many proposals. Please try again later."), frappe.RateLimitExceededError)

	def _guard_status_change(self):
		"""Status changes go through freelance/api.py, which checks who may make
		them (the transition table in freelance/rules.py). A System
		Manager may still correct a record from the desk."""
		if not self.has_value_changed("status") or self.flags.status_via_api:
			return
		if "System Manager" in frappe.get_roles():
			return
		frappe.throw(_("This status change is not allowed."), frappe.PermissionError)

	def _stamp_status_time(self):
		field = proposal_rules.TIMESTAMP_FIELDS.get(self.status)
		if field and not self.get(field) and (self.is_new() or self.has_value_changed("status")):
			self.set(field, now_datetime())
