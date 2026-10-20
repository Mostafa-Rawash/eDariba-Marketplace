"""The one Guest-writable Marketplace endpoint.

Route:
  POST /api/method/edariba_marketplace.api.public.inquiry.submit_inquiry

Wraps the real "استفسار مباشر وسري" form in accountant-profile.php's sidebar
(currently a data-edariba-demo-form that submits nowhere) — once that form
is wired up, it calls this instead of faking success. Rate-limited per
requester_email since this is the only endpoint a Guest can write to.
"""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit


@frappe.whitelist(allow_guest=True)
@rate_limit(key="requester_email", limit=5, seconds=60 * 60)
def submit_inquiry(
	recipient: str,
	requester_name: str,
	requester_email: str,
	requester_phone: str,
	details: str,
	inquiry_type: str = "",
	related_service: str = "",
):
	if not frappe.db.exists("Marketplace Profile", {"name": recipient, "publication_status": "Published"}):
		frappe.throw(_("Recipient not found."))
	doc = frappe.get_doc(
		{
			"doctype": "Marketplace Inquiry",
			"recipient": recipient,
			"related_service": related_service or None,
			"requester_name": requester_name,
			"requester_email": requester_email,
			"requester_phone": requester_phone,
			"inquiry_type": inquiry_type,
			"details": details,
		}
	)
	doc.insert(ignore_permissions=True)
	return {"ok": True}
