import unittest
from datetime import date

from marketplace.freelance import rules as r


class TestProposalTransitions(unittest.TestCase):
	def test_client_moves(self):
		self.assertEqual(r.next_statuses(r.CLIENT, "Submitted"), ("Shortlisted", "Accepted", "Rejected"))
		self.assertEqual(r.next_statuses(r.CLIENT, "Shortlisted"), ("Accepted", "Rejected"))

	def test_freelancer_only_withdraws_active(self):
		self.assertTrue(r.can_transition(r.FREELANCER, "Submitted", "Withdrawn"))
		self.assertTrue(r.can_transition(r.FREELANCER, "Shortlisted", "Withdrawn"))
		for current in ("Accepted", "Rejected", "Withdrawn"):
			self.assertFalse(r.can_transition(r.FREELANCER, current, "Withdrawn"), current)

	def test_freelancer_cannot_accept_own_proposal(self):
		for target in ("Shortlisted", "Accepted", "Rejected"):
			self.assertFalse(r.can_transition(r.FREELANCER, "Submitted", target))

	def test_client_cannot_withdraw_or_reopen(self):
		self.assertFalse(r.can_transition(r.CLIENT, "Submitted", "Withdrawn"))
		self.assertFalse(r.can_transition(r.CLIENT, "Rejected", "Accepted"))
		self.assertFalse(r.can_transition(r.CLIENT, "Accepted", "Rejected"))

	def test_final_statuses_are_final(self):
		for actor in (r.CLIENT, r.FREELANCER):
			for status in ("Accepted", "Rejected", "Withdrawn"):
				self.assertEqual(r.next_statuses(actor, status), ())

	def test_unknown_actor_has_no_moves(self):
		self.assertEqual(r.next_statuses("stranger", "Submitted"), ())

	def test_every_target_status_has_a_timestamp_field(self):
		targets = {s for actor in (r.CLIENT, r.FREELANCER) for c in r.STATUSES for s in r.next_statuses(actor, c)}
		self.assertEqual(targets, set(r.TIMESTAMP_FIELDS))


class TestProposalGuards(unittest.TestCase):
	def test_project_open_only_when_published_and_before_deadline(self):
		today = date(2026, 10, 26)
		self.assertTrue(r.project_open("Published", date(2026, 10, 26), today))
		self.assertTrue(r.project_open("Published", None, today))
		self.assertFalse(r.project_open("Published", date(2026, 10, 25), today))
		for status in ("Draft", "Closed", "Archived", None):
			self.assertFalse(r.project_open(status, date(2027, 1, 1), today), status)

	def test_cover_letter_bounds(self):
		self.assertFalse(r.cover_letter_ok("x" * 79))
		self.assertTrue(r.cover_letter_ok("x" * 80))
		self.assertTrue(r.cover_letter_ok("x" * 2000))
		self.assertFalse(r.cover_letter_ok("x" * 2001))
		self.assertFalse(r.cover_letter_ok(None))
