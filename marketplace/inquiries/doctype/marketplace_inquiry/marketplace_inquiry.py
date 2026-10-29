import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, validate_email_address

from marketplace.inquiries import notifications
from marketplace.inquiries import rules as request_rules

LIFECYCLE_FIELDS = ("first_responded_at", "closed_by", *request_rules.TIMESTAMP_FIELDS.values())


class MarketplaceInquiry(Document):
	"""A request from a logged-in client to one accountant. Created and changed
	only through inquiries/api.py, which applies the business and status rules;
	this controller keeps the invariants that must hold however it is saved."""

	def validate(self):
		if not self.requester:
			frappe.throw(_("A request must belong to a logged-in user."))
		if not self.requester_email or not validate_email_address(self.requester_email):
			frappe.throw(_("A valid email is required."))
		if self.is_new():
			self.created_at = now_datetime()
			self.status = "New"
			return
		if self.has_value_changed("requester"):
			frappe.throw(_("The requester of a request cannot be changed."))
		self._stamp_lifecycle()

	def _stamp_lifecycle(self):
		"""Lifecycle timestamps for the statistics (stats/service.py). Each is
		set the first time and never overwritten, whoever saves the request."""
		before = self.get_doc_before_save()
		for field in LIFECYCLE_FIELDS:
			if before.get(field) and self.get(field) != before.get(field):
				self.set(field, before.get(field))

		now = now_datetime()
		if self.has_value_changed("status"):
			field = request_rules.TIMESTAMP_FIELDS.get(self.status)
			if field and not self.get(field):
				self.set(field, now)
		# The provider's first answer: their first reply, or accepting or
		# declining without one. Editing the reply later changes responded_at only.
		replied = self.has_value_changed("response") and bool(self.response)
		# A support decision is not the provider's answer (no response-time stat, no points).
		decided = (
			self.has_value_changed("status")
			and self.status in request_rules.ANSWER_STATUSES
			and not self.flags.support_action
		)
		if (replied or decided) and not self.first_responded_at:
			self.first_responded_at = now

	def after_insert(self):
		notifications.notify_new_request(self)

	def on_update(self):
		# get_doc_before_save() is None on insert; after_insert covers that case.
		if self.get_doc_before_save() is None:
			return
		if self.flags.support_action:
			notifications.notify_support_update(self)
			return
		if self.has_value_changed("status"):
			event = self.status
		elif self.has_value_changed("response"):
			event = notifications.REPLY_UPDATED
		else:
			return
		notifications.notify_update(self, event, by_requester=frappe.session.user == self.requester)
