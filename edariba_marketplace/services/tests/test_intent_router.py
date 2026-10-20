import unittest

from edariba_marketplace.services.intent_router import classify


class TestIntentRouter(unittest.TestCase):
	def test_project_keyword(self):
		self.assertEqual(classify("أبحث عن مناقصة ضريبية")["entity_type"], "project")

	def test_service_keyword(self):
		self.assertEqual(classify("كام سعر إقرار القيمة المضافة")["entity_type"], "service")

	def test_accountant_keyword(self):
		self.assertEqual(classify("محتاج محاسب قانوني في القاهرة")["entity_type"], "accountant")

	def test_unmatched_defaults_to_accountant_and_flags_unmatched(self):
		result = classify("blah blah")
		self.assertEqual(result["entity_type"], "accountant")
		self.assertFalse(result["matched"])

	def test_category_guess(self):
		self.assertEqual(classify("فحص ضريبة القيمة المضافة")["category"], "tax")
