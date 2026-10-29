import json
import unittest

from marketplace.patches.backfill_inquiry_lifecycle import first_times


def version(at, *changes):
	return {"creation": at, "data": json.dumps({"changed": [list(c) for c in changes]})}


class TestInquiryBackfill(unittest.TestCase):
	def test_first_reply_wins_over_later_edits(self):
		versions = [
			version("t1", ("status", "New", "Responded"), ("response", None, "أهلًا")),
			version("t2", ("response", "أهلًا", "تعديل")),
		]
		self.assertEqual(first_times(versions)["first_responded_at"], "t1")

	def test_accept_without_reply_is_a_first_response(self):
		times = first_times([version("t1", ("status", "New", "Accepted"))])
		self.assertEqual(times, {"first_responded_at": "t1", "accepted_at": "t1"})

	def test_status_times(self):
		times = first_times(
			[
				version("t1", ("status", "New", "Responded")),
				version("t2", ("status", "Responded", "Accepted")),
				version("t3", ("status", "Accepted", "Closed")),
			]
		)
		self.assertEqual(times["accepted_at"], "t2")
		self.assertEqual(times["closed_at"], "t3")

	def test_cancellation_is_not_a_response(self):
		times = first_times([version("t1", ("status", "New", "Cancelled"))])
		self.assertEqual(times, {"cancelled_at": "t1"})

	def test_unknown_history_gives_nothing(self):
		self.assertEqual(first_times([{"creation": "t", "data": "not json"}, {"creation": "t", "data": None}]), {})
