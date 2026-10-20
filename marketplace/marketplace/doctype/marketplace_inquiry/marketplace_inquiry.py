import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, validate_email_address

from marketplace.services import notifications


class MarketplaceInquiry(Document):
	"""A request from a logged-in client to one accountant. Created and changed
	only through api/workspace.py, which applies the business and status rules;
	this controller keeps the invariants that must hold however it is saved."""

	def validate(self):
		if not self.requester:
			frappe.throw(_("A request must belong to a logged-in user."))
		if not self.requester_email or not validate_email_address(self.requester_email):
			frappe.throw(_("A valid email is required."))
		if self.is_new():
			self.created_at = now_datetime()
			self.status = "New"
		elif self.has_value_changed("requester"):
			frappe.throw(_("The requester of a request cannot be changed."))

	def after_insert(self):
		notifications.notify_new_request(self)

	def on_update(self):
		# get_doc_before_save() is None on insert; after_insert covers that case.
		if self.get_doc_before_save() is None or not self.has_value_changed("status"):
			return
		# The requester does not need an email about a change they made themselves.
		if frappe.session.user != self.requester:
			notifications.notify_status_change(self)
