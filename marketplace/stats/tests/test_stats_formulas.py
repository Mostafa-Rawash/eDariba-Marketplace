import unittest
from datetime import date, datetime, timedelta

from marketplace.stats import formulas as f

T0 = datetime(2026, 10, 1, 9, 0)


def h(hours):
	return T0 + timedelta(hours=hours)


class TestRange(unittest.TestCase):
	TODAY = date(2026, 10, 26)

	def test_default_is_last_90_days_inclusive(self):
		start, end = f.parse_range(None, None, self.TODAY)
		self.assertEqual(end, self.TODAY)
		self.assertEqual((end - start).days + 1, 90)

	def test_explicit_range(self):
		self.assertEqual(f.parse_range("2026-10-01", "2026-10-10", self.TODAY), (date(2026, 10, 1), date(2026, 10, 10)))

	def test_rejects_reversed_too_long_and_bad_dates(self):
		with self.assertRaises(f.RangeError):
			f.parse_range("2026-10-10", "2026-10-01", self.TODAY)
		with self.assertRaises(f.RangeError):
			f.parse_range("2024-01-01", "2026-01-01", self.TODAY)
		with self.assertRaises(f.RangeError):
			f.parse_range("not-a-date", None, self.TODAY)


class TestBasics(unittest.TestCase):
	def test_median(self):
		self.assertIsNone(f.median([]))
		self.assertEqual(f.median([3, 1, 2]), 2)
		self.assertEqual(f.median([4, 1, 3, 2]), 2.5)

	def test_rate_needs_minimum_sample(self):
		self.assertIsNone(f.rate(2, 4))
		self.assertEqual(f.rate(3, 5), 0.6)
		self.assertIsNone(f.rate(0, 0, min_sample=0))

	def test_hours_between_ignores_missing_and_negative(self):
		self.assertEqual(f.hours_between(T0, h(1.5)), 1.5)
		self.assertIsNone(f.hours_between(T0, None))
		self.assertIsNone(f.hours_between(h(2), T0))


class TestResponseMetrics(unittest.TestCase):
	def test_rate_and_median(self):
		rows = [
			{"created_at": T0, "status": "Responded", "first_responded_at": h(1)},
			{"created_at": T0, "status": "Accepted", "first_responded_at": h(2)},
			{"created_at": T0, "status": "Declined", "first_responded_at": h(3)},
			{"created_at": T0, "status": "Responded", "first_responded_at": h(60)},  # outside 48h
			{"created_at": T0, "status": "New", "first_responded_at": None},  # unanswered, old
		]
		m = f.response_metrics(rows, now=h(24 * 30))
		self.assertEqual(m["eligible"], 5)
		self.assertEqual(m["answered_within_window"], 3)
		self.assertEqual(m["response_rate"], 0.6)
		self.assertIsNone(m["median_first_response_hours"])  # 4 timings < min sample 5

	def test_median_with_enough_samples(self):
		rows = [{"created_at": T0, "status": "Responded", "first_responded_at": h(x)} for x in (1, 2, 3, 4, 100)]
		self.assertEqual(f.response_metrics(rows, now=h(500))["median_first_response_hours"], 3)

	def test_quick_cancellations_and_young_requests_are_not_held_against_provider(self):
		rows = [
			{"created_at": T0, "status": "Cancelled", "first_responded_at": None, "cancelled_at": h(0.5)},
			{"created_at": h(100), "status": "New", "first_responded_at": None},  # 10h old at now
			{"created_at": T0, "status": "Cancelled", "first_responded_at": None, "cancelled_at": h(5)},  # counts
		]
		m = f.response_metrics(rows, now=h(110))
		self.assertEqual(m["eligible"], 1)
		self.assertEqual(m["answered_within_window"], 0)

	def test_old_answered_requests_without_timestamp_are_left_out(self):
		rows = [{"created_at": T0, "status": "Responded", "first_responded_at": None}]
		self.assertEqual(f.response_metrics(rows, now=h(500))["eligible"], 0)

	def test_edited_reply_does_not_change_first_response(self):
		# first_responded_at is what is measured; responded_at (latest reply) is ignored.
		rows = [{"created_at": T0, "status": "Responded", "first_responded_at": h(1), "responded_at": h(200)}] * 5
		self.assertEqual(f.response_metrics(rows, now=h(500))["median_first_response_hours"], 1)


class TestOutcomes(unittest.TestCase):
	def test_request_outcomes(self):
		rows = (
			[{"status": "Closed", "accepted_at": T0, "closed_at": h(5)}] * 3
			+ [{"status": "Accepted", "accepted_at": T0, "closed_at": None}] * 2
			+ [{"status": "Cancelled"}] * 2
			+ [{"status": "Declined"}]
			+ [{"status": "Closed", "accepted_at": None, "closed_at": None}]  # pre-tracking, excluded from completion
		)
		m = f.request_outcomes(rows)
		self.assertEqual(m["received"], 9)
		self.assertEqual(m["by_status"]["Closed"], 4)
		self.assertEqual(m["completion_rate"], 0.6)
		self.assertEqual(m["cancellation_rate"], round(2 / 9, 4))
		self.assertEqual(m["decline_rate"], round(1 / 9, 4))

	def test_proposal_metrics(self):
		rows = (
			[{"status": "Accepted", "submitted_at": T0, "accepted_at": h(x)} for x in (10, 20, 30, 40, 50)]
			+ [{"status": "Rejected", "submitted_at": T0}] * 5
			+ [{"status": "Submitted", "submitted_at": T0}] * 4
		)
		m = f.proposal_metrics(rows)
		self.assertEqual(m["submitted"], 14)
		self.assertEqual(m["acceptance_rate"], 0.5)  # open ones do not count
		self.assertEqual(m["median_hours_to_acceptance"], 30)

	def test_ctr_needs_impressions(self):
		self.assertIsNone(f.ctr(5, 10))
		self.assertEqual(f.ctr(5, 20), 0.25)
