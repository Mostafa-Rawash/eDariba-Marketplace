import unittest

from marketplace.services import gamification_rules as g


class TestRules(unittest.TestCase):
	def test_defaults(self):
		rules = g.merge_rules(None)
		self.assertEqual(rules[g.SERVICE_PUBLISHED]["points"], 10)
		self.assertTrue(rules[g.PROFILE_COMPLETED]["per_user"])

	def test_valid_overrides_apply(self):
		rules = g.merge_rules({g.SERVICE_PUBLISHED: {"points": 5, "daily_cap": 2}})
		self.assertEqual((rules[g.SERVICE_PUBLISHED]["points"], rules[g.SERVICE_PUBLISHED]["daily_cap"]), (5, 2))

	def test_bad_overrides_are_ignored(self):
		rules = g.merge_rules(
			{
				g.SERVICE_PUBLISHED: {"points": 10**9, "daily_cap": 0},
				g.REQUEST_RESPONDED: {"points": -5, "daily_cap": "lots"},
				g.REQUEST_COMPLETED: {"points": True},
				"self_award": {"points": 1000},
			}
		)
		self.assertEqual(rules[g.SERVICE_PUBLISHED]["points"], 10)
		self.assertEqual(rules[g.SERVICE_PUBLISHED]["daily_cap"], 3)
		self.assertEqual(rules[g.REQUEST_RESPONDED]["points"], 5)
		self.assertEqual(rules[g.REQUEST_COMPLETED]["points"], 20)
		self.assertNotIn("self_award", rules)

	def test_overrides_do_not_mutate_defaults(self):
		g.merge_rules({g.SERVICE_PUBLISHED: {"points": 1}})
		self.assertEqual(g.DEFAULT_RULES[g.SERVICE_PUBLISHED]["points"], 10)

	def test_idempotency_key(self):
		key = g.idempotency_key(g.SERVICE_PUBLISHED, "a@x.com", "Marketplace Service", "s1", per_user=False)
		self.assertEqual(key, "service_published:Marketplace Service:s1")
		# Same record, another user (or a repeat): same key, so awarded once.
		self.assertEqual(key, g.idempotency_key(g.SERVICE_PUBLISHED, "b@x.com", "Marketplace Service", "s1", per_user=False))
		# Per-user events ignore the record: a renamed profile is not a new award.
		self.assertEqual(
			g.idempotency_key(g.PROFILE_COMPLETED, "a@x.com", "Marketplace Profile", "old", per_user=True),
			g.idempotency_key(g.PROFILE_COMPLETED, "a@x.com", "Marketplace Profile", "new", per_user=True),
		)

	def test_daily_cap(self):
		self.assertTrue(g.under_cap(2, 3))
		self.assertFalse(g.under_cap(3, 3))
		self.assertTrue(g.under_cap(10**6, None))

	def test_progress(self):
		self.assertEqual(g.progress(3, 10), {"value": 3, "threshold": 10, "percent": 30, "done": False})
		self.assertTrue(g.progress(12, 10)["done"])
		self.assertEqual(g.progress(12, 10)["percent"], 100)
		self.assertEqual(g.progress(None, 0)["threshold"], 1)
