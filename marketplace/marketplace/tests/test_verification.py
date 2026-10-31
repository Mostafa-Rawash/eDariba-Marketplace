import unittest

from marketplace.marketplace import verification as v


class TestVerificationPolicy(unittest.TestCase):
	def test_bypassed_by_default(self):
		self.assertFalse(v.verification_required({}))
		self.assertTrue(v.verification_required({"marketplace_verification_required": 1}))

	def test_new_profile_is_verified_automatically_while_bypassed(self):
		self.assertEqual(v.status_for_new_profile(False), (v.VERIFIED, v.AUTOMATIC))

	def test_new_profile_is_pending_when_required(self):
		self.assertEqual(v.status_for_new_profile(True), (v.PENDING, None))

	def test_pending_and_empty_become_verified_while_bypassed(self):
		for status in (None, "", v.PENDING):
			self.assertTrue(v.auto_verify(status, required=False), status)

	def test_rejected_is_never_undone_automatically(self):
		self.assertFalse(v.auto_verify(v.REJECTED, required=False))

	def test_nothing_auto_verified_when_required(self):
		self.assertFalse(v.auto_verify(v.PENDING, required=True))

	def test_owner_cannot_self_verify(self):
		for required in (True, False):
			self.assertFalse(v.owner_may_change(v.PENDING, v.VERIFIED, required))
			self.assertFalse(v.owner_may_change(v.REJECTED, v.VERIFIED, required))
			self.assertFalse(v.owner_may_change(v.VERIFIED, v.REJECTED, required))

	def test_owner_resubmits_rejected_only_when_review_exists(self):
		self.assertTrue(v.owner_may_change(v.REJECTED, v.PENDING, required=True))
		self.assertFalse(v.owner_may_change(v.REJECTED, v.PENDING, required=False))

	def test_unchanged_status_is_always_allowed(self):
		self.assertTrue(v.owner_may_change(v.VERIFIED, v.VERIFIED, required=False))
