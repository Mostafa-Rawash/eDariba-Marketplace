"""Office task board rules: who in an accountant's office sees, assigns and
moves which task, and what a valid set of board columns is.

Pure Python (no Frappe), unit-tested in office/test_rules.py. office/access.py
loads the rows and office/api.py applies these rules.

Who is who inside a workspace (accounting/tenant/workspace.py):
- the tenant's Owner runs the office: every task, the columns, assignments;
- a Member invited as an *Employee* works on tasks assigned to them and on the
  tasks of the companies they may use (`allowed_companies`);
- a Member invited as a *Client* (the default) never sees the board.
"""
from datetime import date, timedelta

OWNER = "owner"
EMPLOYEE = "employee"

# Member.member_type
MEMBER_CLIENT = "Client"
MEMBER_EMPLOYEE = "Employee"
MEMBER_TYPES = (MEMBER_CLIENT, MEMBER_EMPLOYEE)

PRIORITIES = ("Low", "Normal", "Urgent")

# (title, is_done) of the columns an office starts with; it can change them.
DEFAULT_COLUMNS = (
	("جديد", 0),
	("قيد التنفيذ", 0),
	("مراجعة", 0),
	("تم", 1),
)
MAX_COLUMNS = 10
COLUMN_TITLE_MAX = 40
TASK_TITLE_MAX = 140

# Done tasks older than this drop off the board (they stay in the database).
BOARD_DONE_DAYS = 30


def office_role(workspace_role, member_type):
	"""OWNER | EMPLOYEE | None from the workspace role ('owner' | 'member' |
	None) and, for a Member, their Member.member_type."""
	if workspace_role == "owner":
		return OWNER
	if workspace_role == "member" and member_type == MEMBER_EMPLOYEE:
		return EMPLOYEE
	return None


def can_see_task(role, user, allowed, assignee, company):
	"""An Owner sees every task of the office. An Employee sees the tasks
	assigned to them and the tasks of the companies they may use."""
	if role == OWNER:
		return True
	if role == EMPLOYEE:
		return assignee == user or bool(company and company in (allowed or []))
	return False


def can_work_on_task(role, user, assignee):
	"""Change the status or tick the checklist: the Owner, or the assignee."""
	return role == OWNER or (role == EMPLOYEE and assignee == user)


def assignee_problem(assignee, owner_user, employees, company):
	"""Why `assignee` cannot take a task (an error code), or None.
	`employees` maps each Active Employee's email to the companies they may use.
	Unassigned is allowed; the Owner can take any task; an Employee only a task
	with no company or with a company they may use."""
	if not assignee or assignee == owner_user:
		return None
	if assignee not in employees:
		return "not_employee"
	if company and company not in (employees.get(assignee) or []):
		return "no_company_access"
	return None


def column_problems(columns):
	"""Error codes for a proposed board, `columns` being a list of
	{"title": str, "is_done": bool} in display order. Empty list = valid."""
	problems = []
	if not columns:
		return ["empty"]
	if len(columns) > MAX_COLUMNS:
		problems.append("too_many")
	titles = [(c.get("title") or "").strip() for c in columns]
	if any(not t for t in titles):
		problems.append("blank_title")
	if any(len(t) > COLUMN_TITLE_MAX for t in titles):
		problems.append("title_too_long")
	if len(set(titles)) != len(titles):
		problems.append("duplicate_title")
	done = [bool(c.get("is_done")) for c in columns]
	if not any(done):
		problems.append("no_done_column")
	if all(done):
		problems.append("no_open_column")
	return problems


def is_overdue(due_date, done, today=None):
	if not due_date or done:
		return False
	return _as_date(due_date) < (today or date.today())


def needs_reminder(due_date, done, today=None):
	"""Not done and due tomorrow, today or earlier: the daily reminder lists it."""
	if not due_date or done:
		return False
	return _as_date(due_date) <= (today or date.today()) + timedelta(days=1)


def _as_date(value):
	if isinstance(value, date):
		return value
	return date.fromisoformat(str(value)[:10])
