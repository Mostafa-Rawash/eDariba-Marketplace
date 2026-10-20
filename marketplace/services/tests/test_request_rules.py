import unittest

from marketplace.services.request_rules import (
	PROVIDER,
	REQUESTER,
	STATUSES,
	can_respond,
	can_transition,
	next_statuses,
)


class TestRequestRules(unittest.TestCase):
	def test_provider_accepts_or_declines_open_request(self):
		for current in ("New", "Responded"):
			self.assertTrue(can_transition(PROVIDER, current, "Accepted"))
			self.assertTrue(can_transition(PROVIDER, current, "Declined"))

	def test_requester_cannot_accept_or_decline(self):
		for current in ("New", "Responded"):
			self.assertFalse(can_transition(REQUESTER, current, "Accepted"))
			self.assertFalse(can_transition(REQUESTER, current, "Declined"))

	def test_only_requester_cancels_and_only_before_accepted(self):
		self.assertTrue(can_transition(REQUESTER, "New", "Cancelled"))
		self.assertTrue(can_transition(REQUESTER, "Responded", "Cancelled"))
		self.assertFalse(can_transition(REQUESTER, "Accepted", "Cancelled"))
		self.assertFalse(can_transition(PROVIDER, "New", "Cancelled"))

	def test_either_party_closes_an_accepted_request(self):
		self.assertTrue(can_transition(PROVIDER, "Accepted", "Closed"))
		self.assertTrue(can_transition(REQUESTER, "Accepted", "Closed"))
		self.assertFalse(can_transition(PROVIDER, "New", "Closed"))

	def test_responded_is_reached_only_by_responding(self):
		for actor in (PROVIDER, REQUESTER):
			for current in STATUSES:
				self.assertFalse(can_transition(actor, current, "Responded"))

	def test_final_statuses_have_no_way_out(self):
		for actor in (PROVIDER, REQUESTER):
			for current in ("Declined", "Closed", "Cancelled"):
				self.assertEqual(next_statuses(actor, current), ())

	def test_only_provider_responds_while_open(self):
		self.assertTrue(can_respond(PROVIDER, "New"))
		self.assertTrue(can_respond(PROVIDER, "Responded"))
		self.assertFalse(can_respond(PROVIDER, "Accepted"))
		self.assertFalse(can_respond(REQUESTER, "New"))

	def test_unknown_actor_gets_nothing(self):
		self.assertFalse(can_transition("someone", "New", "Accepted"))
		self.assertFalse(can_respond("someone", "New"))


if __name__ == "__main__":
	unittest.main()
