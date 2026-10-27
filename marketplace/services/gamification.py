"""Points ledger and achievements (rules: services/gamification_rules.py).

award() is the only way points are created. It is called from server-side
hooks on records the server controls (request, service, profile, proposal),
never from an API parameter. Each award:
- has an idempotency key (unique in Marketplace Points Entry), so the same
  event processed twice awards once;
- respects the event's daily cap per user;
- is skipped for Guest, Administrator, and for self-dealing the server can see
  (a request is never from its own provider: submit_request blocks it).

Gamification never blocks the action that triggered it: every hook catches
its own errors and logs them. It is also independent of verification.
"""

import functools

import frappe
from frappe.utils import now_datetime, nowdate

from marketplace.services import gamification_rules as rules_mod
from marketplace.services import profile_completion
from marketplace.services.profile_handle import profile_of

LEDGER = "Marketplace Points Entry"


def enabled() -> bool:
	return bool((frappe.local.conf or {}).get("marketplace_gamification_enabled", 1))


def rules() -> dict:
	return rules_mod.merge_rules((frappe.local.conf or {}).get("marketplace_gamification_rules"))


def points_balance(user: str) -> int:
	return int(frappe.db.sql(f"select coalesce(sum(points), 0) from `tab{LEDGER}` where user = %s", user)[0][0])


def _awarded_today(user: str, event: str) -> int:
	return frappe.db.count(
		LEDGER, {"user": user, "event_type": event, "awarded_at": [">=", f"{nowdate()} 00:00:00"]}
	)


def award(user: str, event: str, reference_doctype: str | None = None, reference_name: str | None = None) -> str | None:
	"""Award `event`'s points to `user` once. Returns the ledger entry name,
	or None when nothing was awarded (disabled, capped, already awarded)."""
	if not enabled() or not user or user in ("Guest", "Administrator"):
		return None
	rule = rules().get(event)
	if not rule or not rule["points"]:
		return None
	# The unique key settles the common repeat case in one indexed read.
	key = rules_mod.idempotency_key(event, user, reference_doctype, reference_name, rule["per_user"])
	if frappe.db.exists(LEDGER, {"idempotency_key": key}):
		return None
	if rule["daily_cap"] is not None and not rules_mod.under_cap(_awarded_today(user, event), rule["daily_cap"]):
		return None
	entry = frappe.get_doc(
		{
			"doctype": LEDGER,
			"user": user,
			"points": rule["points"],
			"event_type": event,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"idempotency_key": key,
			"awarded_at": now_datetime(),
		}
	)
	try:
		frappe.db.savepoint("mp_points")
		entry.insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		# Lost a race with the same event: the other award stands.
		frappe.db.rollback(save_point="mp_points")
		return None
	evaluate_achievements(user)
	return entry.name


def _safe_hook(fn):
	"""Gamification never blocks the save that triggered it."""

	@functools.wraps(fn)
	def wrapper(doc, method=None):
		try:
			fn(doc)
		except Exception:
			frappe.log_error(title=f"Marketplace gamification: {fn.__name__}")

	return wrapper


# ------------------------------------------------------------------- hooks ---


@_safe_hook
def on_request_update(inquiry):
	responded = inquiry.has_value_changed("first_responded_at") and inquiry.first_responded_at
	completed = inquiry.has_value_changed("status") and inquiry.status == "Closed" and inquiry.accepted_at
	if not (responded or completed):
		return
	provider = frappe.db.get_value("Marketplace Profile", inquiry.recipient, "user")
	if not provider or provider == inquiry.requester:
		return
	if responded:
		award(provider, rules_mod.REQUEST_RESPONDED, inquiry.doctype, inquiry.name)
	if completed:
		award(provider, rules_mod.REQUEST_COMPLETED, inquiry.doctype, inquiry.name)


@_safe_hook
def on_service_update(service):
	if service.publication_status != "Published" or not service.has_value_changed("publication_status"):
		return
	provider = frappe.db.get_value("Marketplace Profile", service.provider, "user")
	award(provider, rules_mod.SERVICE_PUBLISHED, service.doctype, service.name)


@_safe_hook
def on_profile_update(profile):
	if profile_completion.for_doc(profile)["complete"]:
		award(profile.user, rules_mod.PROFILE_COMPLETED, profile.doctype, profile.name)


@_safe_hook
def on_proposal_accepted(proposal):
	project_client = frappe.db.get_value("Marketplace Project", proposal.project, "client")
	if proposal.submitted_by and proposal.submitted_by != project_client:
		award(proposal.submitted_by, rules_mod.PROPOSAL_ACCEPTED, proposal.doctype, proposal.name)


# ------------------------------------------------------------- achievements ---


def metrics_for(user: str) -> dict[str, int]:
	profile = profile_of(user)
	values = dict.fromkeys(rules_mod.METRICS, 0)
	values["points_total"] = points_balance(user)
	values["proposals_accepted"] = frappe.db.count("Marketplace Proposal", {"submitted_by": user, "status": "Accepted"})
	if profile:
		values["profile_complete"] = int(profile_completion.for_doc(frappe.get_doc("Marketplace Profile", profile))["complete"])
		values["services_published"] = frappe.db.count(
			"Marketplace Service", {"provider": profile, "publication_status": "Published"}
		)
		values["requests_responded"] = frappe.db.count(
			"Marketplace Inquiry", {"recipient": profile, "first_responded_at": ["is", "set"]}
		)
		values["requests_completed"] = frappe.db.count(
			"Marketplace Inquiry", {"recipient": profile, "status": "Closed", "accepted_at": ["is", "set"]}
		)
	return values


def evaluate_achievements(user: str) -> list[str]:
	"""Record achievements `user` has newly reached. Returns their codes."""
	definitions = frappe.get_all(
		"Marketplace Achievement", filters={"is_active": 1}, fields=["name", "metric", "threshold"]
	)
	if definitions:
		have = set(frappe.get_all("Marketplace User Achievement", filters={"user": user}, pluck="achievement"))
		definitions = [d for d in definitions if d.name not in have]
	if not definitions:
		return []
	values = metrics_for(user)
	reached = []
	for d in definitions:
		if not rules_mod.progress(values.get(d.metric, 0), d.threshold)["done"]:
			continue
		try:
			frappe.db.savepoint("mp_achievement")
			frappe.get_doc(
				{"doctype": "Marketplace User Achievement", "user": user, "achievement": d.name, "achieved_at": now_datetime()}
			).insert(ignore_permissions=True)
			reached.append(d.name)
		except frappe.DuplicateEntryError:
			frappe.db.rollback(save_point="mp_achievement")
	return reached


def achievements_for(user: str) -> list[dict]:
	definitions = frappe.get_all(
		"Marketplace Achievement",
		filters={"is_active": 1},
		fields=["name", "title", "description", "metric", "threshold"],
		order_by="sort_order asc, threshold asc",
	)
	achieved = dict(
		frappe.get_all(
			"Marketplace User Achievement", filters={"user": user}, fields=["achievement", "achieved_at"], as_list=True
		)
	)
	values = metrics_for(user)
	return [
		{
			"code": d.name,
			"title": d.title,
			"description": d.description,
			"metric": d.metric,
			"progress": rules_mod.progress(values.get(d.metric, 0), d.threshold),
			"achieved_at": achieved.get(d.name),
		}
		for d in definitions
	]
