import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, validate_email_address


class MarketplaceInquiry(Document):
	def validate(self):
		if not self.requester_email or not validate_email_address(self.requester_email):
			frappe.throw(_("A valid email is required."))
		if self.is_new():
			self.created_at = now_datetime()
			self.status = "New"
