"""Status model for a Marketplace Inquiry (a "request" in the app).

Pure Python, no Frappe import, so the rules are unit-tested on their own
(inquiries/tests/test_request_rules.py). inquiries/api.py is the only caller.

  New -> Responded -> Accepted -> Closed
     \\-> Declined  \\-> Declined
  New / Responded -> Cancelled (by the requester)

Support (Marketplace Moderator: sales / customer support) never responds and
never edits the request; it can only end one that a party abandoned, always
with a reason (inquiries/api.py support_set_request_status):
  New / Responded -> Declined (the accountant disappeared)
                  -> Cancelled (the client disappeared, or a wrong request)
  Accepted -> Closed (the work ended or was abandoned)

Responding (writing the reply text) is a separate action from changing the
status: the provider may respond, and update the reply, while the request is
New or Responded, and responding moves it to Responded.
"""

from marketplace.shared.support import support_reason_ok  # noqa: F401

PROVIDER = "provider"
REQUESTER = "requester"
SUPPORT = "support"

STATUSES = ("New", "Responded", "Accepted", "Declined", "Closed", "Cancelled")
OPEN_STATUSES = ("New", "Responded", "Accepted")
RESPONDABLE_STATUSES = ("New", "Responded")
# Moving to one of these is the provider's first answer to a request.
ANSWER_STATUSES = ("Responded", "Accepted", "Declined")
# Lifecycle timestamp set the first time a request reaches each status.
TIMESTAMP_FIELDS = {"Accepted": "accepted_at", "Declined": "declined_at", "Closed": "closed_at", "Cancelled": "cancelled_at"}

_TRANSITIONS = {
	PROVIDER: {
		"New": ("Accepted", "Declined"),
		"Responded": ("Accepted", "Declined"),
		"Accepted": ("Closed",),
	},
	REQUESTER: {
		"New": ("Cancelled",),
		"Responded": ("Cancelled",),
		"Accepted": ("Closed",),
	},
	SUPPORT: {
		"New": ("Declined", "Cancelled"),
		"Responded": ("Declined", "Cancelled"),
		"Accepted": ("Closed",),
	},
}


def next_statuses(actor: str, current: str) -> tuple[str, ...]:
	"""Statuses `actor` may move a request to from `current`."""
	return _TRANSITIONS.get(actor, {}).get(current, ())


def can_transition(actor: str, current: str, new: str) -> bool:
	return new in next_statuses(actor, current)


def can_respond(actor: str, current: str) -> bool:
	return actor == PROVIDER and current in RESPONDABLE_STATUSES
