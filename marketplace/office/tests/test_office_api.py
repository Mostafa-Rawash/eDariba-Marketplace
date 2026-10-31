"""Office task board on a site: who sees and changes what, column rules, the
assignment rules, member types and the daily reminder.

Run: bench --site <site> run-tests --app marketplace --module marketplace.office.tests.test_office_api

The office is an accounting workspace. Its Tenant, Company, Member and
Prefrances rows are written with db_insert (no controller hooks): accounting's
Company and Prefrances hooks create tenants and request ETA tokens, which these
tests must not do. Every test rolls back.
"""

import unittest
from unittest import mock

import frappe
from frappe.utils import add_days, today

from marketplace.office import api, notifications, permissions

OWNER = "office_owner@example.com"
EMPLOYEE = "office_employee@example.com"
CLIENT = "office_client@example.com"
OTHER_OWNER = "office_other@example.com"

T1, T2 = "office-test-tenant-1", "office-test-tenant-2"
C1, C2, C3 = "Office Test Co 1", "Office Test Co 2", "Office Test Co 3"
EMPLOYEE_MEMBER, CLIENT_MEMBER = "office-test-employee", "office-test-client"


def _insert(values):
	if not frappe.db.exists(values["doctype"], values["name"]):
		frappe.get_doc(values).db_insert()


def _user(email):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert(ignore_permissions=True)


def _office():
	for email in (OWNER, EMPLOYEE, CLIENT, OTHER_OWNER):
		_user(email)
	_insert({"doctype": "Tenant", "name": T1, "user": OWNER, "company_name": "Office One"})
	_insert({"doctype": "Tenant", "name": T2, "user": OTHER_OWNER, "company_name": "Office Two"})
	for name, tenant in ((C1, T1), (C2, T1), (C3, T2)):
		_insert({"doctype": "Company", "name": name, "company_name": name, "tenant": tenant, "id": name})
	_insert({
		"doctype": "Member", "name": EMPLOYEE_MEMBER, "email": EMPLOYEE, "tenant": T1,
		"status": "Active", "member_type": "Employee", "allowed_companies": frappe.as_json([C1]),
	})
	_insert({
		"doctype": "Member", "name": CLIENT_MEMBER, "email": CLIENT, "tenant": T1,
		"status": "Active", "member_type": "Client", "allowed_companies": frappe.as_json([C1, C2]),
	})
	for user, tenant, company in ((OWNER, T1, C1), (EMPLOYEE, T1, C1), (CLIENT, T1, C1), (OTHER_OWNER, T2, C3)):
		_insert({"doctype": "Prefrances", "name": user, "user": user, "tenant": tenant, "company": company})


def data(response):
	return response["data"]


class OfficeCase(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		_office()
		self.mail = mock.patch.object(notifications.frappe, "sendmail").start()
		self.addCleanup(mock.patch.stopall)
		self.as_user(OWNER)
		self.columns = data(api.get_board())["columns"]
		self.open_column = self.columns[0]["name"]
		self.done_column = next(c["name"] for c in self.columns if c["is_done"])

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def as_user(self, user):
		frappe.set_user(user)
		frappe.local.workspace_memo = {}  # accounting's per-request workspace lookups

	def new_task(self, **fields):
		self.as_user(OWNER)
		values = {"title": "إقرار ضريبة القيمة المضافة"}
		values.update(fields)
		return data(api.save_task(values))["name"]


class TestColumns(OfficeCase):
	def test_board_starts_with_default_columns(self):
		self.assertEqual([c["title"] for c in self.columns], ["جديد", "قيد التنفيذ", "مراجعة", "تم"])
		self.assertEqual([c["is_done"] for c in self.columns], [False, False, False, True])

	def test_owner_renames_and_reorders_columns(self):
		reordered = [dict(c) for c in reversed(self.columns)]
		reordered[0]["title"] = "منتهية"
		result = data(api.save_columns(reordered))["columns"]
		self.assertEqual(result[0]["title"], "منتهية")
		self.assertEqual(len(result), 4)

	def test_board_needs_a_done_column(self):
		self.assertRaises(frappe.ValidationError, api.save_columns, [dict(c, is_done=False) for c in self.columns])

	def test_column_with_tasks_cannot_be_deleted(self):
		self.new_task()
		remaining = [c for c in self.columns if c["name"] != self.open_column]
		self.assertRaises(frappe.ValidationError, api.save_columns, remaining)

	def test_employee_cannot_change_columns(self):
		self.as_user(EMPLOYEE)
		self.assertRaises(frappe.PermissionError, api.save_columns, self.columns)


class TestAssignment(OfficeCase):
	def test_assign_to_employee_with_company_access(self):
		task = self.new_task(assignee=EMPLOYEE, company=C1)
		self.assertEqual(frappe.db.get_value("Office Task", task, "tenant"), T1)
		self.mail.assert_called()  # "a task was assigned to you"

	def test_cannot_assign_to_a_client(self):
		self.assertRaises(frappe.ValidationError, self.new_task, assignee=CLIENT)

	def test_cannot_assign_employee_outside_their_companies(self):
		self.assertRaises(frappe.ValidationError, self.new_task, assignee=EMPLOYEE, company=C2)

	def test_cannot_use_another_offices_company(self):
		self.assertRaises(frappe.PermissionError, self.new_task, company=C3)

	def test_list_employees(self):
		people = {p["email"]: p for p in data(api.list_employees())}
		self.assertEqual(set(people), {OWNER, EMPLOYEE})
		self.assertEqual(people[EMPLOYEE]["companies"], [C1])


class TestMemberTypes(OfficeCase):
	def test_owner_switches_a_client_to_employee(self):
		self.assertEqual(data(api.member_types())[CLIENT_MEMBER], "Client")
		api.set_member_type(CLIENT_MEMBER, "Employee")
		self.assertEqual(data(api.member_types())[CLIENT_MEMBER], "Employee")
		self.assertIsNotNone(self.new_task(assignee=CLIENT, company=C2))

	def test_unknown_type_and_other_offices_are_refused(self):
		self.assertRaises(frappe.ValidationError, api.set_member_type, CLIENT_MEMBER, "Boss")
		self.as_user(OTHER_OWNER)
		self.assertRaises(frappe.DoesNotExistError, api.set_member_type, CLIENT_MEMBER, "Employee")

	def test_employees_cannot_change_types(self):
		self.as_user(EMPLOYEE)
		self.assertRaises(frappe.PermissionError, api.set_member_type, CLIENT_MEMBER, "Employee")


class TestVisibility(OfficeCase):
	def test_employee_works_on_their_task(self):
		task = self.new_task(assignee=EMPLOYEE, company=C1)
		self.as_user(EMPLOYEE)
		self.assertIn(task, [t["name"] for t in data(api.my_tasks())["tasks"]])
		self.assertTrue(data(api.set_task_status(task, self.done_column))["done_at"])
		self.assertFalse(data(api.set_task_status(task, self.open_column))["done_at"])

	def test_employee_sees_but_cannot_move_others_tasks_on_their_company(self):
		task = self.new_task(assignee=OWNER, company=C1)
		self.as_user(EMPLOYEE)
		self.assertFalse(data(api.get_task(task))["can_work"])
		self.assertRaises(frappe.PermissionError, api.set_task_status, task, self.done_column)

	def test_employee_cannot_see_tasks_of_other_companies(self):
		task = self.new_task(assignee=OWNER, company=C2)
		self.as_user(EMPLOYEE)
		self.assertRaises(frappe.DoesNotExistError, api.get_task, task)

	def test_board_is_owner_only(self):
		self.as_user(EMPLOYEE)
		self.assertRaises(frappe.PermissionError, api.get_board)

	def test_clients_see_nothing(self):
		task = self.new_task(company=C1)
		self.as_user(CLIENT)
		self.assertRaises(frappe.PermissionError, api.my_tasks)
		self.assertRaises(frappe.PermissionError, api.get_task, task)

	def test_other_office_sees_nothing(self):
		task = self.new_task()
		self.as_user(OTHER_OWNER)
		self.assertRaises(frappe.DoesNotExistError, api.get_task, task)
		self.assertNotIn(task, [t["name"] for t in data(api.get_board())["tasks"]])

	def test_list_filter_for_employee(self):
		condition = permissions.task_query(EMPLOYEE)
		for value in (T1, EMPLOYEE, C1):
			self.assertIn(frappe.db.escape(value), condition)
		self.assertEqual(permissions.task_query(CLIENT), "( 1 = 0 )")


class TestChecklistAndComments(OfficeCase):
	def test_checklist_and_comments(self):
		task = self.new_task(assignee=EMPLOYEE, checklist=[{"label": "مراجعة الفواتير"}, {"label": "  "}])
		self.as_user(EMPLOYEE)
		detail = data(api.get_task(task))
		self.assertEqual(len(detail["checklist"]), 1)
		detail = data(api.set_checklist_item(task, detail["checklist"][0]["name"], 1))
		self.assertTrue(detail["checklist"][0]["done"])
		detail = data(api.add_task_comment(task, "تم رفع الفواتير <b>كلها</b>"))
		self.assertEqual(detail["comments"][-1]["by"], EMPLOYEE)
		self.assertNotIn("<b>", detail["comments"][-1]["text"])


class TestReminders(OfficeCase):
	def test_daily_reminder_lists_due_and_overdue_tasks(self):
		self.new_task(title="مستحقة غدا", assignee=EMPLOYEE, due_date=add_days(today(), 1))
		self.new_task(title="متأخرة", assignee=EMPLOYEE, due_date=add_days(today(), -3))
		self.new_task(title="بعيدة", assignee=EMPLOYEE, due_date=add_days(today(), 10))
		self.mail.reset_mock()
		notifications.send_due_reminders()
		calls = [c for c in self.mail.call_args_list if c.kwargs.get("recipients") == [EMPLOYEE]]
		self.assertEqual(len(calls), 1)
		titles = {t["title"] for t in calls[0].kwargs["args"]["tasks"]}
		self.assertTrue({"مستحقة غدا", "متأخرة"} <= titles)
		self.assertNotIn("بعيدة", titles)
