"""Integration tests that need a site (bench --site <site> run-tests --app marketplace
--module marketplace.services.tests.test_marketplace_integration). They create
their own users and records and roll back after each test."""

import inspect
import unittest

import frappe
from frappe.utils import add_days, nowdate

from marketplace.api import gamification as gamification_api
from marketplace.api import proposals as proposals_api
from marketplace.services import event_rules, events, gamification, gamification_rules, privacy, repository

CLIENT = "it_client@example.com"
FREELANCER = "it_freelancer@example.com"
OTHER_FREELANCER = "it_freelancer2@example.com"
STRANGER = "it_stranger@example.com"


def _user(email):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert(ignore_permissions=True)


def _profile(user, slug):
	frappe.set_user("Administrator")
	return frappe.get_doc(
		{
			"doctype": "Marketplace Profile",
			"user": user,
			"profile_type": "Individual",
			"display_name": slug,
			"slug": slug,
			"headline": "Tax",
			"governorate": "القاهرة",
			"experience_years": 5,
			"bio": "Bio",
			"accepts_projects": 1,
			"offers_services": 1,
			"publication_status": "Published",
		}
	).insert(ignore_permissions=True)


def _project(slug):
	frappe.set_user("Administrator")
	if not frappe.db.exists("Marketplace Category", "it-cat"):
		frappe.get_doc({"doctype": "Marketplace Category", "title": "IT", "slug": "it-cat"}).insert(ignore_permissions=True)
	return frappe.get_doc(
		{
			"doctype": "Marketplace Project",
			"title": "Project",
			"slug": slug,
			"category": "it-cat",
			"client": CLIENT,
			"client_display_name": "Client",
			"client_type": "شركة ناشئة",
			"description": "Desc",
			"budget_min": 100,
			"budget_max": 200,
			"currency": "EGP",
			"deadline": add_days(nowdate(), 30),
			"publication_status": "Published",
		}
	).insert(ignore_permissions=True)


def _proposal(project, freelancer_user, profile):
	frappe.set_user(freelancer_user)
	doc = frappe.get_doc(
		{
			"doctype": "Marketplace Proposal",
			"project": project,
			"freelancer": profile,
			"proposed_amount": 150,
			"currency": "EGP",
			"cover_letter": "x" * 100,
		}
	).insert(ignore_permissions=True)
	frappe.set_user("Administrator")
	return doc


class IntegrationCase(unittest.TestCase):
	def setUp(self):
		for email in (CLIENT, FREELANCER, OTHER_FREELANCER, STRANGER):
			_user(email)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()


class TestProposalWorkflow(IntegrationCase):
	def setUp(self):
		super().setUp()
		self.p1 = _profile(FREELANCER, "it-free-1").name
		self.p2 = _profile(OTHER_FREELANCER, "it-free-2").name
		self.project = _project("it-project").name
		self.a = _proposal(self.project, FREELANCER, self.p1).name
		self.b = _proposal(self.project, OTHER_FREELANCER, self.p2).name

	def test_client_accepts_one_and_the_rest_are_rejected(self):
		frappe.set_user(CLIENT)
		proposals_api.set_proposal_status(self.a, "Accepted")
		frappe.set_user("Administrator")
		project = frappe.get_doc("Marketplace Project", self.project)
		self.assertEqual((project.publication_status, project.accepted_proposal), ("Closed", self.a))
		self.assertTrue(project.closed_at)
		self.assertTrue(frappe.db.get_value("Marketplace Proposal", self.a, "accepted_at"))
		self.assertEqual(frappe.db.get_value("Marketplace Proposal", self.b, "status"), "Rejected")

	def test_second_accept_is_refused(self):
		frappe.set_user(CLIENT)
		proposals_api.set_proposal_status(self.a, "Accepted")
		with self.assertRaises(frappe.ValidationError):
			proposals_api.set_proposal_status(self.b, "Accepted")

	def test_freelancer_cannot_accept_and_stranger_sees_nothing(self):
		frappe.set_user(FREELANCER)
		with self.assertRaises(frappe.PermissionError):
			proposals_api.set_proposal_status(self.a, "Accepted")
		frappe.set_user(STRANGER)
		with self.assertRaises(frappe.DoesNotExistError):
			proposals_api.set_proposal_status(self.a, "Rejected")

	def test_withdraw_only_while_active(self):
		frappe.set_user(FREELANCER)
		proposals_api.withdraw_proposal(self.a)
		with self.assertRaises(frappe.PermissionError):
			proposals_api.withdraw_proposal(self.a)

	def test_no_proposals_on_a_closed_project(self):
		frappe.set_user(CLIENT)
		proposals_api.set_proposal_status(self.a, "Accepted")
		with self.assertRaises(frappe.ValidationError):
			_proposal(self.project, STRANGER, _profile(STRANGER, "it-stranger").name)

	def test_accepting_awards_points_once(self):
		frappe.set_user(CLIENT)
		proposals_api.set_proposal_status(self.a, "Accepted")
		frappe.set_user("Administrator")
		self.assertEqual(
			frappe.db.count(gamification.LEDGER, {"user": FREELANCER, "event_type": gamification_rules.PROPOSAL_ACCEPTED}), 1
		)


class TestPointsLedger(IntegrationCase):
	def test_same_event_awards_once(self):
		first = gamification.award(FREELANCER, gamification_rules.REQUEST_RESPONDED, "Marketplace Inquiry", "it-req-1")
		second = gamification.award(FREELANCER, gamification_rules.REQUEST_RESPONDED, "Marketplace Inquiry", "it-req-1")
		self.assertTrue(first)
		self.assertIsNone(second)

	def test_daily_cap(self):
		cap = gamification.rules()[gamification_rules.SERVICE_PUBLISHED]["daily_cap"]
		results = [
			gamification.award(FREELANCER, gamification_rules.SERVICE_PUBLISHED, "Marketplace Service", f"it-svc-{i}")
			for i in range(cap + 2)
		]
		self.assertEqual(sum(1 for r in results if r), cap)

	def test_entries_are_append_only(self):
		name = gamification.award(FREELANCER, gamification_rules.REQUEST_COMPLETED, "Marketplace Inquiry", "it-req-2")
		entry = frappe.get_doc(gamification.LEDGER, name)
		entry.points = 9999
		with self.assertRaises(frappe.PermissionError):
			entry.save(ignore_permissions=True)
		with self.assertRaises(frappe.PermissionError):
			entry.delete(ignore_permissions=True)

	def test_no_endpoint_accepts_points_or_user(self):
		for fn in (gamification_api.my_points, gamification_api.my_achievements):
			params = set(inspect.signature(fn).parameters)
			self.assertFalse(params & {"points", "user", "event_type"}, fn.__name__)

	def test_guest_and_administrator_get_nothing(self):
		for user in ("Guest", "Administrator"):
			self.assertIsNone(gamification.award(user, gamification_rules.REQUEST_RESPONDED, "Marketplace Inquiry", "x"))

	def test_achievement_reached_once(self):
		if not frappe.db.exists("Marketplace Achievement", "it-points"):
			frappe.get_doc(
				{"doctype": "Marketplace Achievement", "code": "it-points", "title": "IT", "metric": "points_total", "threshold": 1}
			).insert(ignore_permissions=True)
		gamification.award(FREELANCER, gamification_rules.REQUEST_RESPONDED, "Marketplace Inquiry", "it-req-3")
		self.assertEqual(gamification.evaluate_achievements(FREELANCER), [])  # already recorded by award()
		self.assertTrue(
			frappe.db.exists("Marketplace User Achievement", {"user": FREELANCER, "achievement": "it-points"})
		)


class TestEvents(IntegrationCase):
	def setUp(self):
		super().setUp()
		self.profile = _profile(FREELANCER, "it-events").name

	def test_view_counts_every_time_but_visitor_once_a_day(self):
		vhash = events.visitor_hash("visitor-1")
		events.record_view(event_rules.PROFILE_VIEW, "Marketplace Profile", self.profile, vhash)
		events.record_view(event_rules.PROFILE_VIEW, "Marketplace Profile", self.profile, vhash)
		self.assertEqual(
			frappe.db.count("Marketplace Activity", {"event_type": "profile_view", "reference_name": self.profile}), 1
		)
		total = frappe.db.get_value(
			"Marketplace Daily Metric", {"metric": "profile_view", "reference_name": self.profile}, "count"
		)
		self.assertEqual(total, 2)

	def test_click_only_on_a_returned_result(self):
		search_id = frappe.generate_hash(length=16)
		events.write_search(search_id, "tax", "accountant", [event_rules.ref("accountant", self.profile)], 1, "h")
		vhash = events.visitor_hash("visitor-2")
		self.assertFalse(events.record_click(search_id, "accountant", "it-not-returned", vhash))
		self.assertTrue(events.record_click(search_id, "accountant", self.profile, vhash))
		self.assertFalse(events.record_click(search_id, "accountant", self.profile, vhash))  # duplicate

	def test_no_result_search_is_counted(self):
		events.write_search(frappe.generate_hash(length=16), "nothing", "service", [], 0, "h")
		self.assertTrue(frappe.db.exists("Marketplace Daily Metric", {"metric": "search_no_result", "metric_date": nowdate()}))


class TestPrivacyAndCounts(IntegrationCase):
	def test_owner_email_hidden_from_other_users(self):
		profile = _profile(FREELANCER, "it-privacy")
		frappe.set_user(STRANGER)
		doc = frappe.get_doc("Marketplace Profile", profile.name)
		privacy.mask_identity(doc)
		self.assertIsNone(doc.owner)
		frappe.set_user(FREELANCER)
		doc = frappe.get_doc("Marketplace Profile", profile.name)
		privacy.mask_identity(doc)
		self.assertTrue(doc.owner)

	def test_published_service_count_beyond_one_page(self):
		profile = _profile(FREELANCER, "it-count").name
		frappe.set_user("Administrator")
		for i in range(25):
			frappe.get_doc(
				{
					"doctype": "Marketplace Service",
					"title": f"S{i}",
					"slug": f"it-count-s{i}",
					"provider": profile,
					"currency": "EGP",
					"price_unit": "Total",
					"description": "D",
					"publication_status": "Published",
				}
			).insert(ignore_permissions=True)
		self.assertEqual(len(repository.published_services_for_provider(profile)), 20)
		self.assertEqual(repository.count_published_services(profile), 25)
