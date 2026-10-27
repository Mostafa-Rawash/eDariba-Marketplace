"""Proposal status actions for the app (logged-in only).

Routes (POST):
  /api/method/marketplace.api.proposals.set_proposal_status   {name, status}
  /api/method/marketplace.api.proposals.withdraw_proposal     {name}

Normal users hold no write DocPerm on Marketplace Proposal, so these are the
only way to shortlist, accept, reject or withdraw one. Who the caller is comes
from the session; their side of the proposal decides what they may do
(services/proposal_rules.py):

- the project's client shortlists, accepts or rejects, while the project is
  Published;
- the freelancer who submitted it withdraws it while it is active.

Accepting is single-winner: the project row is locked, a second Accepted
proposal is refused, the project is Closed (closed_at, accepted_proposal) and
the other active proposals are Rejected. Nobody is e-mailed yet; see
STATISTICS_AND_GAMIFICATION_BACKEND_IMPLEMENTATION.md.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

from marketplace.api.common import ok
from marketplace.services import gamification, proposal_rules


def _load_as_party(name: str):
	"""The proposal and the caller's side of it. Anyone else gets the same
	'not found' as for a missing id, so proposal ids cannot be probed."""
	user = frappe.session.user
	if name and frappe.db.exists("Marketplace Proposal", name):
		doc = frappe.get_doc("Marketplace Proposal", name)
		if doc.submitted_by == user:
			return doc, proposal_rules.FREELANCER
		if frappe.db.get_value("Marketplace Project", doc.project, "client") == user:
			return doc, proposal_rules.CLIENT
	frappe.throw(_("Proposal not found."), frappe.DoesNotExistError)


def serialize(doc) -> dict:
	return {
		"name": doc.name,
		"project": doc.project,
		"status": doc.status,
		"submitted_at": doc.submitted_at,
		**{field: doc.get(field) for field in proposal_rules.TIMESTAMP_FIELDS.values()},
	}


def _set_status(doc, status: str):
	doc.flags.status_via_api = True
	doc.status = status
	doc.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def set_proposal_status(name: str, status: str):
	doc, actor = _load_as_party(name)
	if status not in proposal_rules.STATUSES:
		frappe.throw(_("Unknown status."))
	if not proposal_rules.can_transition(actor, doc.status, status):
		if status == "Withdrawn":
			frappe.throw(_("Only an active proposal can be withdrawn."), frappe.PermissionError)
		frappe.throw(_("This status change is not allowed."), frappe.PermissionError)

	if actor == proposal_rules.CLIENT:
		# Locked for the rest of the transaction: two accepts at once run one
		# after the other.
		project = frappe.db.get_value(
			"Marketplace Project", doc.project, ["name", "publication_status"], as_dict=True, for_update=True
		)
		if not project or project.publication_status != "Published":
			frappe.throw(_("This project is not open for proposals."))
		if status == "Accepted" and frappe.db.exists(
			"Marketplace Proposal", {"project": doc.project, "status": "Accepted", "name": ["!=", doc.name]}
		):
			frappe.throw(_("This project already has an accepted proposal."))

	_set_status(doc, status)
	if status == "Accepted":
		_close_project_on_hire(doc)
		gamification.on_proposal_accepted(doc)
	return ok(serialize(doc))


@frappe.whitelist(methods=["POST"])
def withdraw_proposal(name: str):
	return set_proposal_status(name, "Withdrawn")


def _close_project_on_hire(accepted):
	project = frappe.get_doc("Marketplace Project", accepted.project)
	project.publication_status = "Closed"
	project.accepted_proposal = accepted.name
	if not project.closed_at:
		project.closed_at = now_datetime()
	project.flags.hire_via_api = True
	project.save(ignore_permissions=True)

	others = frappe.get_all(
		"Marketplace Proposal",
		filters={
			"project": accepted.project,
			"name": ["!=", accepted.name],
			"status": ["in", list(proposal_rules.ACTIVE_STATUSES)],
		},
		pluck="name",
	)
	for other in others:
		_set_status(frappe.get_doc("Marketplace Proposal", other), "Rejected")
