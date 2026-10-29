"""Logged-in marketplace actions for the app (app.edariba.com).

Routes (POST, session cookie through the SPA's /logic proxy):
  /api/method/marketplace.inquiries.api.submit_request
  /api/method/marketplace.inquiries.api.list_requests
  /api/method/marketplace.inquiries.api.get_request
  /api/method/marketplace.inquiries.api.respond_request
  /api/method/marketplace.inquiries.api.set_request_status
  /api/method/marketplace.inquiries.api.support_set_request_status  (support team)

Every function is @frappe.whitelist() without allow_guest, so Frappe rejects
guests before any code here runs. Normal users hold no DocPerm on Marketplace
Inquiry, so these functions are the only way they can create or change one.
Each function therefore does its own checks:

- who the user is comes from frappe.session.user, never from the request;
- only the fields an action needs are accepted;
- whether the user is the requester or the provider decides what they may do
  (inquiries/rules.py), and is re-checked on every call;
- responses carry only the fields the screens need.

The support team (Marketplace Moderator) may read any request through
get_request, with the reply history, and may end an abandoned one through
support_set_request_status with a reason. It never responds and never edits
the request text or the reply.

Saves use ignore_permissions=True for that reason: the checks above replace
the DocPerm check, and the DocType controller still enforces its invariants.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_to_date, now_datetime

from marketplace.inquiries import rules as request_rules
from marketplace.marketplace import profile_handle
from marketplace.shared.filters import clamp_page, clamp_page_size
from marketplace.shared.permissions import is_moderator
from marketplace.shared.responses import ok

# Per logged-in user, counted from the requests table itself, so it cannot be
# reset by changing an email address or IP.
REQUEST_LIMIT_PER_HOUR = 10

_LIST_FIELDS = ["name", "recipient", "related_service", "inquiry_type", "status", "created_at", "responded_at"]


def _user() -> str:
	return frappe.session.user


def _my_profile(user: str) -> str | None:
	return frappe.db.get_value("Marketplace Profile", {"user": user}, "name")


def _load_as_party(name: str, allow_support: bool = False):
	"""The request and the caller's side of it. Anyone who is neither the
	requester nor the provider gets the same 'not found' as for a missing id,
	so request ids cannot be probed. With allow_support, staff who are not a
	party get the SUPPORT side."""
	user = _user()
	# exists() first: get_doc on a missing name would also queue its own
	# "not found" message for the client.
	doc = frappe.get_doc("Marketplace Inquiry", name) if frappe.db.exists("Marketplace Inquiry", name) else None
	if doc is not None:
		if doc.requester == user:
			return doc, request_rules.REQUESTER
		if frappe.db.get_value("Marketplace Profile", doc.recipient, "user") == user:
			return doc, request_rules.PROVIDER
		if allow_support and is_moderator(user):
			return doc, request_rules.SUPPORT
	frappe.throw(_("Request not found."), frappe.DoesNotExistError)


def _serialize(doc, actor: str) -> dict:
	profile = frappe.db.get_value("Marketplace Profile", doc.recipient, ["display_name", "slug"], as_dict=True) or {}
	out = {
		"name": doc.name,
		"role": actor,
		"status": doc.status,
		"inquiry_type": doc.inquiry_type,
		"details": doc.details,
		"created_at": doc.created_at,
		"response": doc.response,
		"responded_at": doc.responded_at,
		"recipient": {"name": doc.recipient, "display_name": profile.get("display_name"), "slug": profile.get("slug")},
		"related_service": None,
		"next_statuses": list(request_rules.next_statuses(actor, doc.status)),
		"can_respond": request_rules.can_respond(actor, doc.status),
		"support_note": doc.support_note,
	}
	if doc.related_service:
		service = frappe.db.get_value("Marketplace Service", doc.related_service, ["title", "slug"], as_dict=True) or {}
		out["related_service"] = {"name": doc.related_service, "title": service.get("title"), "slug": service.get("slug")}
	if actor in (request_rules.PROVIDER, request_rules.SUPPORT):
		# The provider needs the client's contact details to do the work.
		out["requester"] = {"name": doc.requester_name, "email": doc.requester_email, "phone": doc.requester_phone}
	if actor == request_rules.SUPPORT:
		# Support follows up with both sides and checks what was sent.
		user = frappe.db.get_value("Marketplace Profile", doc.recipient, "user")
		out["recipient"]["email"] = frappe.db.get_value("User", user, "email") if user else None
		out["closed_by"] = doc.closed_by
		out["reply_history"] = _reply_history(doc.name)
	return out


def _reply_history(name: str) -> list[dict]:
	"""Every version of the provider's reply, oldest first, from Frappe's
	Version log (Inquiry has track_changes). Read-only, for support."""
	history = []
	for version in frappe.get_all(
		"Version",
		filters={"ref_doctype": "Marketplace Inquiry", "docname": name},
		fields=["data", "creation"],
		order_by="creation asc",
	):
		try:
			changed = json.loads(version.data or "{}").get("changed") or []
		except ValueError:
			continue
		for field, old, new in changed:
			if field == "response":
				history.append({"at": version.creation, "previous": old, "reply": new})
	return history


@frappe.whitelist(methods=["POST"])
def submit_request(
	recipient: str,
	details: str,
	inquiry_type: str | None = None,
	related_service: str | None = None,
	phone: str | None = None,
):
	user = _user()
	details = (details or "").strip()
	if not details:
		frappe.throw(_("Please describe what you need."))

	# Reading the caller's User row FOR UPDATE locks it for the rest of this
	# request's transaction, so two simultaneous submits by the same user run
	# one after the other and the duplicate and rate checks below cannot both
	# pass before either insert.
	account = frappe.db.get_value("User", user, ["full_name", "email", "mobile_no"], as_dict=True, for_update=True)

	# A request link shared before the accountant changed username carries the
	# old slug; store the profile's current name.
	recipient = profile_handle.owner_of_slug(recipient) or recipient
	profile = frappe.db.get_value(
		"Marketplace Profile",
		recipient,
		["user", "publication_status", "offers_services"],
		as_dict=True,
	)
	# Published and offering services is enough: owners activate their own
	# profiles, so verification does not gate requests.
	if not profile or profile.publication_status != "Published" or not profile.offers_services:
		frappe.throw(_("This accountant is not available for requests."))
	if profile.user == user:
		frappe.throw(_("You cannot send a request to yourself."))

	if related_service:
		service = frappe.db.get_value(
			"Marketplace Service", related_service, ["provider", "publication_status"], as_dict=True
		)
		if not service or service.provider != recipient or service.publication_status != "Published":
			frappe.throw(_("This service is not available from this accountant."))

	if frappe.db.exists(
		"Marketplace Inquiry",
		{"requester": user, "recipient": recipient, "status": ["in", list(request_rules.OPEN_STATUSES)]},
	):
		frappe.throw(_("You already have an open request with this accountant."))

	recent = frappe.db.count(
		"Marketplace Inquiry",
		{"requester": user, "creation": [">", add_to_date(now_datetime(), hours=-1)]},
	)
	if recent >= REQUEST_LIMIT_PER_HOUR:
		frappe.throw(_("You have sent too many requests. Please try again later."), frappe.RateLimitExceededError)

	doc = frappe.get_doc(
		{
			"doctype": "Marketplace Inquiry",
			"recipient": recipient,
			"related_service": related_service or None,
			"inquiry_type": inquiry_type or None,
			"details": details,
			"requester": user,
			"requester_name": account.full_name or account.email,
			"requester_email": account.email,
			"requester_phone": (phone or "").strip() or account.mobile_no,
		}
	)
	doc.insert(ignore_permissions=True)
	return ok(_serialize(doc, request_rules.REQUESTER))


@frappe.whitelist()
def list_requests(box: str = "sent", status: str | None = None, page: int = 1, page_size: int = 20):
	"""box="sent": requests I sent. box="received": requests to my profile."""
	user = _user()
	page = clamp_page(page)
	page_size = clamp_page_size(page_size)

	if box == "sent":
		filters = {"requester": user}
	elif box == "received":
		profile = _my_profile(user)
		if not profile:
			return ok([], page=page, page_size=page_size, total=0, meta={"box": box})
		filters = {"recipient": profile}
	else:
		frappe.throw(_("box must be 'sent' or 'received'."))

	if status:
		if status not in request_rules.STATUSES:
			frappe.throw(_("Unknown status."))
		filters["status"] = status

	fields = _LIST_FIELDS + (["requester_name"] if box == "received" else [])
	rows = frappe.get_all(
		"Marketplace Inquiry",
		filters=filters,
		fields=fields,
		order_by="creation desc",
		limit_start=(page - 1) * page_size,
		limit_page_length=page_size,
		ignore_permissions=True,
	)
	total = frappe.db.count("Marketplace Inquiry", filters=filters)

	names = list({r.recipient for r in rows})
	display = dict(
		frappe.get_all(
			"Marketplace Profile",
			filters={"name": ["in", names]},
			fields=["name", "display_name"],
			as_list=True,
			ignore_permissions=True,
		)
	) if names else {}
	for row in rows:
		row["recipient_display_name"] = display.get(row.recipient)

	return ok(rows, page=page, page_size=page_size, total=total, meta={"box": box, "status": status})


@frappe.whitelist()
def get_request(name: str):
	doc, actor = _load_as_party(name, allow_support=True)
	return ok(_serialize(doc, actor))


@frappe.whitelist(methods=["POST"])
def respond_request(name: str, message: str):
	"""The provider's reply. Moves the request to Responded; may be sent again
	to update the reply while the request is still New or Responded. The
	requester is emailed each time (see MarketplaceInquiry.on_update)."""
	doc, actor = _load_as_party(name)
	if not request_rules.can_respond(actor, doc.status):
		frappe.throw(_("You cannot respond to this request."), frappe.PermissionError)
	if not (message or "").strip():
		frappe.throw(_("Please write a reply."))

	doc.response = message.strip()
	doc.responded_at = now_datetime()
	doc.status = "Responded"
	doc.save(ignore_permissions=True)
	return ok(_serialize(doc, actor))


@frappe.whitelist(methods=["POST"])
def set_request_status(name: str, status: str):
	doc, actor = _load_as_party(name)
	if not request_rules.can_transition(actor, doc.status, status):
		frappe.throw(_("This status change is not allowed."), frappe.PermissionError)

	doc.status = status
	if status == "Closed" and not doc.closed_by:
		doc.closed_by = actor
	doc.save(ignore_permissions=True)
	return ok(_serialize(doc, actor))


@frappe.whitelist(methods=["POST"])
def support_set_request_status(name: str, status: str, reason: str):
	"""Support ends a request a party abandoned (inquiries/rules.py SUPPORT):
	Declined when the accountant disappeared, Cancelled when the client did or
	the request was wrong, Closed for an Accepted one. The reason is required,
	stored in support_note, logged as a comment, and both parties are emailed.
	Support that is itself a party to the request uses the normal actions."""
	doc, actor = _load_as_party(name, allow_support=True)
	if actor != request_rules.SUPPORT or not request_rules.can_transition(actor, doc.status, status):
		frappe.throw(_("This status change is not allowed."), frappe.PermissionError)
	if not request_rules.support_reason_ok(reason):
		frappe.throw(_("Please write the reason for this change (10 to 500 characters)."))

	reason = reason.strip()
	doc.status = status
	doc.support_note = reason
	if status == "Closed" and not doc.closed_by:
		doc.closed_by = request_rules.SUPPORT
	doc.flags.support_action = True
	doc.save(ignore_permissions=True)
	doc.add_comment("Info", _("Support ({0}) changed the status to {1}: {2}").format(_user(), status, reason))
	return ok(_serialize(doc, actor))


@frappe.whitelist(methods=["POST"])
def sync_profile_link():
	"""Make the caller's public profile link match their username (the link
	follows the username, see marketplace/profile_handle.py). Only renames the
	caller's own profile. Returns {"slug": current slug or null}."""
	return ok({"slug": profile_handle.sync_my_profile_link(_user())})
