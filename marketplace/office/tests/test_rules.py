"""Pure coverage of the office task rules (no database)."""
import unittest
from datetime import date

from marketplace.office.rules import (
	EMPLOYEE, MEMBER_CLIENT, MEMBER_EMPLOYEE, OWNER, assignee_problem, can_see_task,
	can_work_on_task, column_problems, is_overdue, needs_reminder, office_role,
)


class TestOfficeRoles(unittest.TestCase):
	def test_owner_runs_the_office(self):
		self.assertEqual(office_role("owner", None), OWNER)

	def test_only_employee_members_work_on_the_board(self):
		self.assertEqual(office_role("member", MEMBER_EMPLOYEE), EMPLOYEE)
		self.assertIsNone(office_role("member", MEMBER_CLIENT))
		self.assertIsNone(office_role("member", None))
		self.assertIsNone(office_role(None, MEMBER_EMPLOYEE))


class TestTaskVisibility(unittest.TestCase):
	def test_owner_sees_every_task(self):
		self.assertTrue(can_see_task(OWNER, "o@x", None, "e@x", "C1"))

	def test_employee_sees_own_tasks_and_allowed_companies(self):
		self.assertTrue(can_see_task(EMPLOYEE, "e@x", [], "e@x", None))
		self.assertTrue(can_see_task(EMPLOYEE, "e@x", ["C1"], "other@x", "C1"))
		self.assertFalse(can_see_task(EMPLOYEE, "e@x", ["C1"], "other@x", "C2"))
		self.assertFalse(can_see_task(EMPLOYEE, "e@x", ["C1"], "other@x", None))

	def test_clients_and_strangers_see_nothing(self):
		self.assertFalse(can_see_task(None, "c@x", ["C1"], "c@x", "C1"))

	def test_only_owner_or_assignee_works_on_a_task(self):
		self.assertTrue(can_work_on_task(OWNER, "o@x", "e@x"))
		self.assertTrue(can_work_on_task(EMPLOYEE, "e@x", "e@x"))
		self.assertFalse(can_work_on_task(EMPLOYEE, "e@x", "other@x"))
		self.assertFalse(can_work_on_task(None, "e@x", "e@x"))


class TestAssignment(unittest.TestCase):
	employees = {"e@x": ["C1"]}

	def test_unassigned_and_owner_are_always_fine(self):
		self.assertIsNone(assignee_problem(None, "o@x", self.employees, "C9"))
		self.assertIsNone(assignee_problem("o@x", "o@x", self.employees, "C9"))

	def test_employee_needs_access_to_the_company(self):
		self.assertIsNone(assignee_problem("e@x", "o@x", self.employees, "C1"))
		self.assertIsNone(assignee_problem("e@x", "o@x", self.employees, None))
		self.assertEqual(assignee_problem("e@x", "o@x", self.employees, "C2"), "no_company_access")

	def test_clients_cannot_be_assigned(self):
		self.assertEqual(assignee_problem("client@x", "o@x", self.employees, None), "not_employee")


class TestColumns(unittest.TestCase):
	def cols(self, *spec):
		return [{"title": t, "is_done": d} for t, d in spec]

	def test_default_shape_is_valid(self):
		self.assertEqual(column_problems(self.cols(("جديد", 0), ("تم", 1))), [])

	def test_needs_open_and_done_columns(self):
		self.assertIn("no_done_column", column_problems(self.cols(("A", 0), ("B", 0))))
		self.assertIn("no_open_column", column_problems(self.cols(("A", 1))))
		self.assertEqual(column_problems([]), ["empty"])

	def test_titles(self):
		self.assertIn("blank_title", column_problems(self.cols((" ", 0), ("تم", 1))))
		self.assertIn("duplicate_title", column_problems(self.cols(("A", 0), ("A", 1))))
		self.assertIn("title_too_long", column_problems(self.cols(("x" * 41, 0), ("تم", 1))))

	def test_at_most_ten(self):
		spec = [("c%d" % i, 0) for i in range(10)] + [("done", 1)]
		self.assertIn("too_many", column_problems(self.cols(*spec)))


class TestDueDates(unittest.TestCase):
	today = date(2026, 10, 29)

	def test_overdue(self):
		self.assertTrue(is_overdue("2026-10-28", False, self.today))
		self.assertFalse(is_overdue("2026-10-29", False, self.today))
		self.assertFalse(is_overdue("2026-10-28", True, self.today))
		self.assertFalse(is_overdue(None, False, self.today))

	def test_reminder_covers_tomorrow_and_earlier(self):
		self.assertTrue(needs_reminder("2026-10-30", False, self.today))
		self.assertTrue(needs_reminder(date(2026, 10, 1), False, self.today))
		self.assertFalse(needs_reminder("2026-10-31", False, self.today))
		self.assertFalse(needs_reminder("2026-10-29", True, self.today))
