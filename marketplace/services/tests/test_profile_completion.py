import unittest

from marketplace.services import profile_completion as pc

FULL = {
	"display_name": "أحمد",
	"headline": "محاسب قانوني",
	"governorate": "القاهرة",
	"avatar": "/files/a.png",
	"bio": "<p>" + "ن" * 80 + "</p>",
	"experience_years": 5,
	"specialties": [{"label": "الفحص الضريبي"}, {"label": "ضريبة الدخل"}, {"label": "تأسيس الشركات"}],
	"qualifications": [{"title": "زمالة"}],
	"case_study_title": "حالة",
}


class TestProfileCompletion(unittest.TestCase):
	def test_full_profile_is_complete(self):
		result = pc.completion(FULL)
		self.assertEqual(result["percent"], 100)
		self.assertTrue(result["complete"])
		self.assertEqual([i["key"] for i in result["items"]], [k for k, _ in pc.ITEMS])

	def test_empty_profile_is_zero(self):
		result = pc.completion({})
		self.assertEqual(result["percent"], 0)
		self.assertFalse(result["complete"])

	def test_bio_html_and_spaces_do_not_count(self):
		profile = dict(FULL, bio="<p>" + "&nbsp; " * 100 + "قصير</p>")
		self.assertFalse(pc.item_states(profile)["bio_experience"])

	def test_invalid_experience_does_not_count(self):
		for years in (0, -3, 500, "abc", None):
			self.assertFalse(pc.item_states(dict(FULL, experience_years=years))["bio_experience"], years)

	def test_blank_or_duplicate_specialties_do_not_count(self):
		profile = dict(FULL, specialties=[{"label": "أ"}, {"label": " أ "}, {"label": "  "}, {"label": "ب"}])
		self.assertFalse(pc.item_states(profile)["specialties"])

	def test_blank_qualification_title_does_not_count(self):
		self.assertFalse(pc.item_states(dict(FULL, qualifications=[{"title": "  "}]))["qualifications"])

	def test_whitespace_basics_do_not_count(self):
		self.assertFalse(pc.item_states(dict(FULL, headline="   "))["basics"])

	def test_percent_rounds_by_items(self):
		self.assertEqual(pc.completion(dict(FULL, case_study_title=""))["percent"], 80)

	def test_publish_rule_is_unchanged(self):
		self.assertEqual(pc.publish_problems(FULL), [])
		self.assertEqual(
			pc.publish_problems({"bio": "<p> </p>", "headline": "", "experience_years": None}),
			["bio", "headline", "experience_years"],
		)
		# 0 years is allowed to publish, as before.
		self.assertEqual(pc.publish_problems(dict(FULL, experience_years=0)), [])
