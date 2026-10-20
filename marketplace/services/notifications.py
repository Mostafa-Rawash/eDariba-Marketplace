"""Request emails. Queued through frappe.sendmail (Email Queue), so a save
never waits on, or fails because of, the mail server.

Emails carry only the requester's display name and a link into the app
(app.edariba.com/marketplace/requests/<id>); the details are shown after
login, never in the email body.
"""

import frappe

DEFAULT_APP_URL = "https://app.edariba.com"


def request_url(name: str) -> str:
	base = (frappe.conf.get("marketplace_app_url") or DEFAULT_APP_URL).rstrip("/")
	return f"{base}/marketplace/requests/{name}"


def _send(recipient: str | None, subject: str, template: str, args: dict, doc) -> None:
	if not recipient:
		return
	try:
		frappe.sendmail(
			recipients=[recipient],
			subject=subject,
			template=template,
			args=args,
			reference_doctype=doc.doctype,
			reference_name=doc.name,
			delayed=True,
		)
	except Exception:
		# A notification must never roll back the request it is about.
		frappe.log_error(title="Marketplace request email failed", message=frappe.get_traceback())


def notify_new_request(doc) -> None:
	"""To the accountant who received the request."""
	provider_user = frappe.db.get_value("Marketplace Profile", doc.recipient, "user")
	email = frappe.db.get_value("User", provider_user, "email") if provider_user else None
	_send(
		email,
		"طلب جديد على eDariba",
		"marketplace_new_request",
		{"requester_name": doc.requester_name, "url": request_url(doc.name)},
		doc,
	)


def notify_status_change(doc) -> None:
	"""To the requester, when the accountant responds or the status changes."""
	provider_name = frappe.db.get_value("Marketplace Profile", doc.recipient, "display_name")
	_send(
		doc.requester_email,
		"تحديث على طلبك في eDariba",
		"marketplace_request_update",
		{"provider_name": provider_name, "status": doc.status, "url": request_url(doc.name)},
		doc,
	)
