"""Status model for a Marketplace Inquiry (a "request" in the app).

Pure Python, no Frappe import, so the rules are unit-tested on their own
(services/tests/test_request_rules.py). api/workspace.py is the only caller.

  New -> Responded -> Accepted -> Closed
     \\-> Declined  \\-> Declined
  New / Responded -> Cancelled (by the requester)

Responding (writing the reply text) is a separate action from changing the
status: the provider may respond, and update the reply, while the request is
New or Responded, and responding moves it to Responded.
"""

PROVIDER = "provider"
REQUESTER = "requester"

STATUSES = ("New", "Responded", "Accepted", "Declined", "Closed", "Cancelled")
OPEN_STATUSES = ("New", "Responded", "Accepted")
RESPONDABLE_STATUSES = ("New", "Responded")

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
}


def next_statuses(actor: str, current: str) -> tuple[str, ...]:
	"""Statuses `actor` may move a request to from `current`."""
	return _TRANSITIONS.get(actor, {}).get(current, ())


def can_transition(actor: str, current: str, new: str) -> bool:
	return new in next_statuses(actor, current)


def can_respond(actor: str, current: str) -> bool:
	return actor == PROVIDER and current in RESPONDABLE_STATUSES
