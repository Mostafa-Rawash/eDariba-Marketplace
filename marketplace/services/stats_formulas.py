"""Statistics formulas over plain rows (dicts with datetimes).

Pure Python, unit-tested in services/tests/test_stats_formulas.py.
services/stats.py loads the rows and calls these.

Conventions:
- a rate is None, not 0, when the sample is smaller than MIN_SAMPLE, so a
  screen can say "not enough data" instead of showing a misleading number;
- times are medians in hours (one slow outlier does not dominate);
- rows missing a lifecycle timestamp are left out of the formulas that need
  it (requests from before the timestamps existed), never guessed.
"""

from datetime import date, datetime, timedelta

from marketplace.services.proposal_rules import STATUSES as PROPOSAL_STATUSES
from marketplace.services.request_rules import STATUSES as REQUEST_STATUSES

MIN_SAMPLE = 5
RESPONSE_WINDOW_HOURS = 48
# A request cancelled this soon after sending, unanswered, was a mistake, not
# a chance to respond.
CANCEL_GRACE_HOURS = 1
DEFAULT_RANGE_DAYS = 90
MAX_RANGE_DAYS = 366


class RangeError(ValueError):
	pass


def parse_range(date_from, date_to, today: date) -> tuple[date, date]:
	"""Inclusive (from, to). Defaults to the last DEFAULT_RANGE_DAYS days."""

	def as_date(value):
		if value in (None, ""):
			return None
		if isinstance(value, datetime):
			return value.date()
		if isinstance(value, date):
			return value
		try:
			return date.fromisoformat(str(value)[:10])
		except ValueError:
			raise RangeError(f"Invalid date: {value}") from None

	end = as_date(date_to) or today
	start = as_date(date_from) or end - timedelta(days=DEFAULT_RANGE_DAYS - 1)
	if start > end:
		raise RangeError("from_date is after to_date.")
	if (end - start).days + 1 > MAX_RANGE_DAYS:
		raise RangeError(f"The range can be at most {MAX_RANGE_DAYS} days.")
	return start, end


def median(values: list[float]) -> float | None:
	values = sorted(v for v in values if v is not None)
	if not values:
		return None
	mid = len(values) // 2
	return values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2


def rate(numerator: int, denominator: int, min_sample: int = MIN_SAMPLE) -> float | None:
	if denominator < max(min_sample, 1):
		return None
	return round(numerator / denominator, 4)


def hours_between(start: datetime | None, end: datetime | None) -> float | None:
	if not start or not end or end < start:
		return None
	return round((end - start).total_seconds() / 3600, 2)


def count_by(rows: list[dict], field: str, keys: tuple[str, ...]) -> dict[str, int]:
	counts = {k: 0 for k in keys}
	for row in rows:
		if row.get(field) in counts:
			counts[row[field]] += 1
	return counts


def response_metrics(requests: list[dict], now: datetime | None = None, min_sample: int = MIN_SAMPLE) -> dict:
	"""Requests received by a provider: rows with created_at, status,
	first_responded_at, cancelled_at.

	response_rate = answered within RESPONSE_WINDOW_HOURS / eligible, where
	eligible leaves out requests cancelled unanswered within CANCEL_GRACE_HOURS,
	requests still New that are younger than the window (they may yet be
	answered in time), and answered requests with no first_responded_at."""
	eligible = 0
	answered_in_window = 0
	hours = []
	for row in requests:
		created = row.get("created_at")
		first = row.get("first_responded_at")
		if not created:
			continue
		if not first:
			if row.get("status") in ("Responded", "Accepted", "Declined", "Closed"):
				# Answered before first_responded_at was recorded and not
				# back-filled: the time is unknown, so leave it out.
				continue
			grace = hours_between(created, row.get("cancelled_at"))
			if grace is not None and grace <= CANCEL_GRACE_HOURS:
				continue
			age = hours_between(created, now)
			if row.get("status") == "New" and age is not None and age < RESPONSE_WINDOW_HOURS:
				continue
		eligible += 1
		took = hours_between(created, first)
		if took is not None:
			hours.append(took)
			if took <= RESPONSE_WINDOW_HOURS:
				answered_in_window += 1
	return {
		"eligible": eligible,
		"answered_within_window": answered_in_window,
		"response_rate": rate(answered_in_window, eligible, min_sample),
		"median_first_response_hours": median(hours) if len(hours) >= min_sample else None,
		"window_hours": RESPONSE_WINDOW_HOURS,
	}


def request_outcomes(requests: list[dict], min_sample: int = MIN_SAMPLE) -> dict:
	"""completion_rate: of requests accepted (accepted_at set), the share later
	closed. cancellation_rate: requester cancellations over all received."""
	by_status = count_by(requests, "status", REQUEST_STATUSES)
	accepted = [r for r in requests if r.get("accepted_at")]
	completed = [r for r in accepted if r.get("closed_at")]
	received = len(requests)
	return {
		"received": received,
		"by_status": by_status,
		"completion_rate": rate(len(completed), len(accepted), min_sample),
		"cancellation_rate": rate(by_status["Cancelled"], received, min_sample),
		"decline_rate": rate(by_status["Declined"], received, min_sample),
	}


def proposal_metrics(proposals: list[dict], min_sample: int = MIN_SAMPLE) -> dict:
	"""acceptance_rate = Accepted / (Accepted + Rejected): decided proposals
	only, so open ones do not drag it down. median_hours_to_acceptance from
	submitted_at to accepted_at."""
	by_status = count_by(proposals, "status", PROPOSAL_STATUSES)
	decided = by_status["Accepted"] + by_status["Rejected"]
	to_accept = [hours_between(p.get("submitted_at"), p.get("accepted_at")) for p in proposals if p.get("accepted_at")]
	to_accept = [h for h in to_accept if h is not None]
	return {
		"submitted": len(proposals),
		"by_status": by_status,
		"acceptance_rate": rate(by_status["Accepted"], decided, min_sample),
		"median_hours_to_acceptance": median(to_accept) if len(to_accept) >= min_sample else None,
	}


def ctr(clicks: int, impressions: int, min_sample: int = 20) -> float | None:
	return rate(clicks, impressions, min_sample)
