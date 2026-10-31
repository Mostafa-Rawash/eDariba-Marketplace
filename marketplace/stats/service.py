"""Statistics read models: load rows, apply stats/formulas.py.

Every number comes from stored records. Where the source only exists since
this code was deployed (activity events, lifecycle timestamps), the result
says so in "collected_since" instead of presenting a partial history as
complete. Nothing is extrapolated or backfilled with invented data.
"""

import frappe
from frappe.utils import getdate, now_datetime, today

from marketplace.marketplace import profile_completion
from marketplace.marketplace.profile_handle import profile_of
from marketplace.stats import formulas as stats_formulas

PROFILE = "Marketplace Profile"
SERVICE = "Marketplace Service"
REQUEST_FIELDS = ["status", "created_at", "first_responded_at", "accepted_at", "declined_at", "closed_at", "cancelled_at"]
PROPOSAL_FIELDS = ["status", "submitted_at", "accepted_at"]


def date_range(from_date=None, to_date=None):
	try:
		return stats_formulas.parse_range(from_date, to_date, getdate(today()))
	except stats_formulas.RangeError as e:
		frappe.throw(str(e), frappe.ValidationError)


def _bounds(start, end) -> dict:
	return {"start": f"{start} 00:00:00", "end": f"{end} 23:59:59.999999"}


def _requests_and_proposals(request_filters: dict, proposal_filters: dict) -> dict:
	requests = frappe.get_all("Marketplace Inquiry", filters=request_filters, fields=REQUEST_FIELDS, ignore_permissions=True)
	proposals = frappe.get_all(
		"Marketplace Proposal", filters=proposal_filters, fields=PROPOSAL_FIELDS, ignore_permissions=True
	)
	return {
		"requests": {
			**stats_formulas.request_outcomes(requests),
			**stats_formulas.response_metrics(requests, now=now_datetime()),
		},
		"proposals": stats_formulas.proposal_metrics(proposals),
	}


def _metric_sums(start, end, doctype: str, names: list[str]) -> dict[str, int]:
	if not names:
		return {}
	rows = frappe.db.sql(
		"""
		select metric, sum(`count`) from `tabMarketplace Daily Metric`
		where metric_date between %(start)s and %(end)s
			and reference_doctype = %(dt)s and reference_name in %(names)s
		group by metric
		""",
		{"start": start, "end": end, "dt": doctype, "names": tuple(names)},
	)
	return {metric: int(total or 0) for metric, total in rows}


def _unique_visitors(start, end, event: str, doctype: str, names: list[str]) -> int:
	if not names:
		return 0
	return frappe.db.count(
		"Marketplace Activity",
		{
			"event_type": event,
			"reference_doctype": doctype,
			"reference_name": ["in", names],
			"event_date": ["between", [str(start), str(end)]],
		},
	)


def _collected_since() -> str | None:
	first = frappe.db.sql("select min(metric_date) from `tabMarketplace Daily Metric`")
	return str(first[0][0]) if first and first[0][0] else None


def activity_for(start, end, doctype: str, names: list[str], view_metric: str) -> dict:
	sums = _metric_sums(start, end, doctype, names)
	impressions = sums.get("search_impression", 0)
	clicks = sums.get("search_click", 0)
	return {
		"views": sums.get(view_metric, 0),
		"unique_visitor_days": _unique_visitors(start, end, view_metric, doctype, names),
		"search_impressions": impressions,
		"search_clicks": clicks,
		"search_ctr": stats_formulas.ctr(clicks, impressions),
	}


def provider_stats(user: str, from_date=None, to_date=None) -> dict:
	"""The signed-in provider's own numbers. Scoped to their profile only."""
	start, end = date_range(from_date, to_date)
	profile = profile_of(user)
	if not profile:
		frappe.throw("Profile not found.", frappe.DoesNotExistError)
	doc = frappe.get_doc(PROFILE, profile)
	in_range = ["between", list(_bounds(start, end).values())]
	services = frappe.get_all(SERVICE, filters={"provider": profile}, fields=["name", "publication_status"], ignore_permissions=True)
	service_names = [s.name for s in services]

	return {
		"range": {"from": str(start), "to": str(end)},
		"min_sample": stats_formulas.MIN_SAMPLE,
		**_requests_and_proposals(
			{"recipient": profile, "created_at": in_range}, {"submitted_by": user, "submitted_at": in_range}
		),
		"services": {
			"total": len(services),
			"by_status": stats_formulas.count_by(services, "publication_status", ("Draft", "Published", "Unpublished")),
		},
		"profile_activity": activity_for(start, end, PROFILE, [profile], "profile_view"),
		"service_activity": activity_for(start, end, SERVICE, service_names, "service_view"),
		"completion": profile_completion.for_doc(doc),
		"collected_since": {"activity": _collected_since()},
	}


def own_completion(user: str) -> dict:
	profile = profile_of(user)
	if not profile:
		frappe.throw("Profile not found.", frappe.DoesNotExistError)
	return profile_completion.for_doc(frappe.get_doc(PROFILE, profile))


# -------------------------------------------------------------------- admin ---


def _group_count(doctype: str, field: str, filters: dict | None = None) -> dict[str, int]:
	rows = frappe.get_all(
		doctype,
		filters=filters or {},
		fields=[field, "count(name) as n"],
		group_by=field,
		ignore_permissions=True,
	)
	return {(r.get(field) or "(none)"): int(r.n) for r in rows}


def admin_stats(from_date=None, to_date=None) -> dict:
	start, end = date_range(from_date, to_date)
	bounds = _bounds(start, end)
	in_range = ["between", list(bounds.values())]

	users = frappe.db.sql(
		"select user_type, enabled, count(*) from `tabUser` where name not in ('Guest', 'Administrator') group by user_type, enabled"
	)
	roles = frappe.db.sql(
		"""
		select role, count(distinct parent) from `tabHas Role`
		where parenttype = 'User' and role in ('Invoicing Owner', 'Marketplace Moderator', 'System Manager')
		group by role
		"""
	)
	metrics = frappe.db.sql(
		"""
		select metric, sum(`count`) from `tabMarketplace Daily Metric`
		where metric_date between %(start)s and %(end)s group by metric
		""",
		{"start": start, "end": end},
	)
	no_result_queries = frappe.db.sql(
		"""
		select query_text, count(*) as n from `tabMarketplace Activity`
		where event_type = 'search' and result_count = 0 and event_date between %(start)s and %(end)s
			and ifnull(query_text, '') != ''
		group by query_text having n >= 2 order by n desc limit 20
		""",
		{"start": start, "end": end},
	)
	errors = frappe.db.sql(
		"""
		select method, count(*) from `tabError Log`
		where creation between %(start)s and %(end)s
			and (method like '%%arketplace%%' or error like '%%marketplace/%%')
		group by method order by count(*) desc limit 20
		""",
		bounds,
	)
	points = frappe.db.sql(
		"""
		select count(distinct user), coalesce(sum(points), 0) from `tabMarketplace Points Entry`
		where awarded_at between %(start)s and %(end)s
		""",
		bounds,
	)

	return {
		"range": {"from": str(start), "to": str(end)},
		"users": {
			"by_type_and_status": [
				{"user_type": t, "enabled": bool(e), "count": int(n)} for t, e, n in users
			],
			"by_role": {role: int(n) for role, n in roles},
		},
		# Current totals (not limited to the range).
		"profiles": {
			"by_publication_status": _group_count(PROFILE, "publication_status"),
			"by_verification_status": _group_count(PROFILE, "verification_status"),
			"by_verification_method": _group_count(PROFILE, "verification_method"),
			"created_in_range": frappe.db.count(PROFILE, {"creation": in_range}),
		},
		"services": {
			"by_publication_status": _group_count(SERVICE, "publication_status"),
			"created_in_range": frappe.db.count(SERVICE, {"creation": in_range}),
		},
		"projects": {
			"by_publication_status": _group_count("Marketplace Project", "publication_status"),
			"created_in_range": frappe.db.count("Marketplace Project", {"creation": in_range}),
		},
		# Created in the range.
		**_requests_and_proposals({"created_at": in_range}, {"submitted_at": in_range}),
		"activity": {metric: int(n or 0) for metric, n in metrics},
		"search": {
			"no_result_queries": [{"query": q, "count": int(n)} for q, n in no_result_queries],
		},
		"errors": [{"method": m, "count": int(n)} for m, n in errors],
		"gamification": {"users_awarded": int(points[0][0] or 0), "points_awarded": int(points[0][1] or 0)},
		"collected_since": {"activity": _collected_since()},
	}
