"""Point rules and achievement metrics. Pure Python, unit-tested in
services/tests/test_gamification_rules.py; services/gamification.py applies
them.

Points are only ever awarded by the server, for events it can verify from its
own records (a published service, a provider's first answer to a request from
another user, a request closed after being accepted, an accepted proposal,
a complete profile). No API takes a points value. Each award has an
idempotency key, so processing the same event twice awards once, and a daily
cap per user per event limits farming.

Points and achievements are kept apart from verification: nothing here reads
or writes verification_status, and nothing should treat points as trust.

Site config can override values (never add events):
  "marketplace_gamification_enabled": 0          turns awarding off
  "marketplace_gamification_rules": {"service_published": {"points": 5, "daily_cap": 2}}
"""

PROFILE_COMPLETED = "profile_completed"
SERVICE_PUBLISHED = "service_published"
REQUEST_RESPONDED = "request_responded"
REQUEST_COMPLETED = "request_completed"
PROPOSAL_ACCEPTED = "proposal_accepted"

# points: awarded once per key; daily_cap: max awards of this event per user
# per day (None = no cap); per_user: the key is the user, not the record, so
# it is awarded once per account (a renamed profile does not count again).
DEFAULT_RULES = {
	PROFILE_COMPLETED: {"points": 50, "daily_cap": None, "per_user": True},
	SERVICE_PUBLISHED: {"points": 10, "daily_cap": 3, "per_user": False},
	REQUEST_RESPONDED: {"points": 5, "daily_cap": 10, "per_user": False},
	REQUEST_COMPLETED: {"points": 20, "daily_cap": 5, "per_user": False},
	PROPOSAL_ACCEPTED: {"points": 15, "daily_cap": 5, "per_user": False},
}

MAX_POINTS_PER_EVENT = 1000
MAX_DAILY_CAP = 100

# Achievement metrics (Marketplace Achievement.metric) and what they count.
METRICS = {
	"profile_complete": "Profile checklist complete (1 or 0)",
	"services_published": "Published services",
	"requests_responded": "Requests answered (first response recorded)",
	"requests_completed": "Requests closed after being accepted",
	"proposals_accepted": "Accepted proposals",
	"points_total": "Total points",
}


def merge_rules(overrides) -> dict:
	"""DEFAULT_RULES with valid overrides applied. Unknown events and bad
	values are ignored, so a typo in site_config cannot create an event or
	award absurd points."""
	rules = {event: dict(rule) for event, rule in DEFAULT_RULES.items()}
	if not isinstance(overrides, dict):
		return rules
	for event, override in overrides.items():
		if event not in rules or not isinstance(override, dict):
			continue
		points = override.get("points")
		if isinstance(points, int) and not isinstance(points, bool) and 0 <= points <= MAX_POINTS_PER_EVENT:
			rules[event]["points"] = points
		if "daily_cap" in override:
			cap = override["daily_cap"]
			if cap is None or (isinstance(cap, int) and not isinstance(cap, bool) and 1 <= cap <= MAX_DAILY_CAP):
				rules[event]["daily_cap"] = cap
	return rules


def idempotency_key(event: str, user: str, reference_doctype: str | None, reference_name: str | None, per_user: bool) -> str:
	if per_user:
		return f"{event}:{user}"
	return f"{event}:{reference_doctype}:{reference_name}"


def under_cap(awarded_today: int, cap: int | None) -> bool:
	return cap is None or awarded_today < cap


def progress(value: int, threshold: int) -> dict:
	threshold = max(int(threshold or 1), 1)
	value = max(int(value or 0), 0)
	return {"value": value, "threshold": threshold, "percent": min(100, round(value * 100 / threshold)), "done": value >= threshold}
