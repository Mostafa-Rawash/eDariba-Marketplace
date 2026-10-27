"""Status model and guards for a Marketplace Proposal.

Pure Python, no Frappe import, so the rules are unit-tested on their own
(services/tests/test_proposal_rules.py). api/proposals.py and the DocType
controller are the callers.

  Submitted -> Shortlisted -> Accepted
           \\-> Accepted    \\-> Rejected
           \\-> Rejected
  Submitted / Shortlisted -> Withdrawn (by the freelancer)

The client (the project's owner) shortlists, accepts and rejects; the
freelancer who submitted it withdraws. Accepting closes the project and
rejects the other active proposals (api/proposals.py).
"""

from datetime import date

CLIENT = "client"
FREELANCER = "freelancer"

STATUSES = ("Submitted", "Shortlisted", "Accepted", "Rejected", "Withdrawn")
ACTIVE_STATUSES = ("Submitted", "Shortlisted")

_TRANSITIONS = {
	CLIENT: {
		"Submitted": ("Shortlisted", "Accepted", "Rejected"),
		"Shortlisted": ("Accepted", "Rejected"),
	},
	FREELANCER: {
		"Submitted": ("Withdrawn",),
		"Shortlisted": ("Withdrawn",),
	},
}

# Status -> the timestamp field set the first time a proposal reaches it.
TIMESTAMP_FIELDS = {
	"Shortlisted": "shortlisted_at",
	"Accepted": "accepted_at",
	"Rejected": "rejected_at",
	"Withdrawn": "withdrawn_at",
}

COVER_LETTER_MIN = 80
COVER_LETTER_MAX = 2000
PROPOSALS_PER_HOUR = 10


def next_statuses(actor: str, current: str) -> tuple[str, ...]:
	return _TRANSITIONS.get(actor, {}).get(current, ())


def can_transition(actor: str, current: str, new: str) -> bool:
	return new in next_statuses(actor, current)


def project_open(publication_status: str | None, deadline: date | None, today: date) -> bool:
	"""A project takes proposals while Published and not past its deadline."""
	if publication_status != "Published":
		return False
	return deadline is None or deadline >= today


def cover_letter_ok(text: str) -> bool:
	return COVER_LETTER_MIN <= len(text or "") <= COVER_LETTER_MAX
