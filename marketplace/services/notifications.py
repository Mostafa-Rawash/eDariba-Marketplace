"""Request emails. Queued through frappe.sendmail (Email Queue), so a save
never waits on, or fails because of, the mail server.

Who is emailed: a new request goes to the accountant. After that, every
change goes to the other side from the person who made it: the provider's
reply, reply edits, accept/decline/close go to the requester; the
requester's cancel/close goes to the provider. Nobody is emailed about their
own change.

Emails carry only a display name and a link into the app
(app.edariba.com/marketplace/requests/<id>); the details are shown after
login, never in the email body.
"""

import frappe

DEFAULT_APP_URL = "https://app.edariba.com"

# Event names passed to templates/emails/marketplace_request_update.html.
REPLY_UPDATED = "ReplyUpdated"


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


def _provider(doc) -> tuple[str | None, str | None]:
	"""(email, display name) of the accountant who received the request."""
	profile = frappe.db.get_value("Marketplace Profile", doc.recipient, ["user", "display_name"], as_dict=True) or {}
	email = frappe.db.get_value("User", profile.get("user"), "email") if profile.get("user") else None
	return email, profile.get("display_name")


def notify_new_request(doc) -> None:
	"""To the accountant who received the request."""
	email, _name = _provider(doc)
	_send(
		email,
		"طلب جديد على eDariba",
		"marketplace_new_request",
		{"requester_name": doc.requester_name, "url": request_url(doc.name)},
		doc,
	)


def notify_update(doc, event: str, by_requester: bool) -> None:
	"""`event` is the new status, or REPLY_UPDATED when only the reply text
	changed. Goes to the side that did not make the change."""
	provider_email, provider_name = _provider(doc)
	if by_requester:
		recipient, actor_name = provider_email, doc.requester_name
	else:
		recipient, actor_name = doc.requester_email, provider_name
	_send(
		recipient,
		"تحديث على طلب في eDariba",
		"marketplace_request_update",
		{"actor_name": actor_name, "event": event, "url": request_url(doc.name)},
		doc,
	)
