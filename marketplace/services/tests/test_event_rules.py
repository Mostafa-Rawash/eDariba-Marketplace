import unittest

from marketplace.services import event_rules as e


class TestEventRules(unittest.TestCase):
	def test_bots_and_missing_agents_are_excluded(self):
		self.assertTrue(e.is_bot(None))
		self.assertTrue(e.is_bot(""))
		for agent in ("Googlebot/2.1", "facebookexternalhit/1.1", "WhatsApp/2.0", "HeadlessChrome", "curl/8"):
			self.assertTrue(e.is_bot(agent), agent)
		self.assertFalse(e.is_bot("Mozilla/5.0 (Windows NT 10.0) Chrome/130.0"))

	def test_visitor_hash_rotates_daily_and_hides_the_key(self):
		a = e.visitor_hash("secret", "2026-10-26", "v:abc")
		self.assertEqual(a, e.visitor_hash("secret", "2026-10-26", "v:abc"))
		self.assertNotEqual(a, e.visitor_hash("secret", "2026-10-27", "v:abc"))
		self.assertNotEqual(a, e.visitor_hash("other", "2026-10-26", "v:abc"))
		self.assertNotIn("abc", a)
		self.assertEqual(len(a), 32)

	def test_dedupe_key_is_stable_per_parts(self):
		self.assertEqual(e.dedupe_key("profile_view", "2026-10-26", "p", "h"), e.dedupe_key("profile_view", "2026-10-26", "p", "h"))
		self.assertNotEqual(e.dedupe_key("profile_view", "2026-10-26", "p", "h"), e.dedupe_key("profile_view", "2026-10-27", "p", "h"))

	def test_queries_are_normalised_masked_and_truncated(self):
		self.assertEqual(e.normalise_query("  إقرار   القيمة  "), "إقرار القيمة")
		self.assertEqual(e.normalise_query("رقم 123456789 و 12"), "رقم # و 12")
		self.assertEqual(len(e.normalise_query("x" * 500)), e.QUERY_MAX_CHARS)
		self.assertEqual(e.normalise_query(None), "")

	def test_only_views_and_clicks_are_trackable(self):
		self.assertNotIn(e.SEARCH, e.TRACKABLE)
		self.assertEqual(set(e.TRACKABLE), {e.PROFILE_VIEW, e.SERVICE_VIEW, e.SEARCH_CLICK})
