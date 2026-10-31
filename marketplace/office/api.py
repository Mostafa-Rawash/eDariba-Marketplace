"""Office task board for accountants' offices (app.edariba.com).

Routes: /api/method/marketplace.office.api.<function>. Responses use the
marketplace envelope (shared/responses.py ok).

Every method works inside the caller's active workspace and reads the caller
from the session. App users hold no DocPerm on the office DocTypes, so these
methods are the only way they read or change them; each checks who the caller
is itself (office/rules.py) and saves with ignore_permissions.

  Owner:     get_board, save_task, delete_task, save_columns, list_employees,
             member_types, set_member_type
  Owner and the task's assignee: set_task_status, set_checklist_item
  Owner and Employees who can see the task: my_tasks, get_task, add_task_comment
  Anyone signed in: my_office_role (never raises)
  Clients (Members invited as Client) get a PermissionError everywhere.
"""
import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, get_fullname, getdate, now_datetime, today

from marketplace.office import access, rules
from marketplace.office.access import COLUMN, TASK
from marketplace.shared.responses import ok

CARD_FIELDS = [
	"name", "title", "company", "assignee", "due_date", "priority", "board_column", "done_at", "modified",
]
EDITABLE_FIELDS = ("title", "description", "company", "assignee", "due_date", "priority", "board_column")
COLUMN_ERRORS = {
	"empty": "Add at least one column",
	"too_many": "A board can have up to 10 columns",
	"blank_title": "Every column needs a title",
	"title_too_long": "Column titles are limited to 40 characters",
	"duplicate_title": "Column titles must be different",
	"no_done_column": "Mark at least one column as done",
	"no_open_column": "Keep at least one column that is not done",
}


def _cards(rows, done_columns):
	"""Board cards: the row plus display names, overdue flag and checklist counts."""
	now = getdate(today())
	names = [row.name for row in rows]
	progress = {}
	if names:
		for item in frappe.get_all(
			"Office Task Checklist Item",
			filters={"parent": ["in", names], "parenttype": TASK},
			fields=["parent", "done"],
		):
			total, done = progress.get(item.parent, (0, 0))
			progress[item.parent] = (total + 1, done + (1 if item.done else 0))
	company_names = _names("Company", "company_name", {row.company for row in rows})
	for row in rows:
		total, done = progress.get(row.name, (0, 0))
		row["company_name"] = company_names.get(row.company)
		row["assignee_name"] = get_fullname(row.assignee) if row.assignee else None
		row["overdue"] = rules.is_overdue(row.due_date, row.board_column in done_columns, now)
		row["checklist_total"], row["checklist_done"] = total, done
	return rows


def _names(doctype, field, names):
	names = [n for n in names if n]
	if not names:
		return {}
	return dict(frappe.get_all(doctype, filters={"name": ["in", names]}, fields=["name", field], as_list=True))


def _columns_payload(tenant):
	return [
		{"name": c.name, "title": c.title, "is_done": bool(c.is_done)} for c in access.columns(tenant)
	]


@frappe.whitelist()
def get_board(company=None, assignee=None, due=None):
	"""The owner's read-only board: columns and task cards, newest activity
	first inside each column. Done tasks older than BOARD_DONE_DAYS are left
	out. `due`: "overdue" | "week" (due within 7 days) | empty."""
	user = frappe.session.user
	tenant, _role, _allowed = access.require_office(user, owner=True)
	columns = _columns_payload(tenant)
	done_columns = {c["name"] for c in columns if c["is_done"]}

	filters = {"tenant": tenant}
	if company:
		filters["company"] = company
	if assignee:
		filters["assignee"] = assignee
	if due == "week":
		filters["due_date"] = ["between", [today(), add_days(today(), 7)]]
	elif due == "overdue":
		filters["due_date"] = ["<", today()]
	rows = frappe.get_all(TASK, filters=filters, fields=CARD_FIELDS, order_by="modified desc", limit_page_length=1000)

	cutoff = get_datetime(add_days(now_datetime(), -rules.BOARD_DONE_DAYS))
	rows = [r for r in rows if not (r.done_at and get_datetime(r.done_at) < cutoff)]
	if due == "overdue":
		rows = [r for r in rows if r.board_column not in done_columns]
	return ok({"columns": columns, "tasks": _cards(rows, done_columns)})


@frappe.whitelist()
def my_tasks(include_done=0):
	"""Tasks assigned to the caller in the active workspace, with the columns
	(so the app can group them and offer the status choices)."""
	user = frappe.session.user
	tenant, _role, _allowed = access.require_office(user)
	columns = _columns_payload(tenant)
	done_columns = {c["name"] for c in columns if c["is_done"]}
	filters = {"tenant": tenant, "assignee": user}
	if not frappe.utils.cint(include_done):
		filters["done_at"] = ["is", "not set"]
	rows = frappe.get_all(TASK, filters=filters, fields=CARD_FIELDS, order_by="modified desc", limit_page_length=500)
	# Soonest due first; tasks without a due date last.
	rows.sort(key=lambda r: (r.due_date is None, str(r.due_date or "")))
	return ok({"columns": columns, "tasks": _cards(rows, done_columns)})


@frappe.whitelist()
def get_task(name):
	user = frappe.session.user
	doc, (_tenant, role, _allowed) = access.load_task(name, user)
	return ok(_detail(doc, user, role))


def _detail(doc, user, role):
	comments = frappe.get_all(
		"Comment",
		filters={"reference_doctype": TASK, "reference_name": doc.name, "comment_type": "Comment"},
		fields=["content", "comment_email", "creation"],
		order_by="creation asc",
	)
	return {
		"name": doc.name,
		"title": doc.title,
		"description": doc.description,
		"company": doc.company,
		"company_name": frappe.db.get_value("Company", doc.company, "company_name") if doc.company else None,
		"assignee": doc.assignee,
		"assignee_name": get_fullname(doc.assignee) if doc.assignee else None,
		"due_date": doc.due_date,
		"priority": doc.priority,
		"board_column": doc.board_column,
		"done_at": doc.done_at,
		"created_by": doc.owner,
		"created_by_name": get_fullname(doc.owner),
		"checklist": [{"name": r.name, "label": r.label, "done": bool(r.done)} for r in doc.checklist],
		"comments": [
			{"text": c.content, "by": c.comment_email, "by_name": get_fullname(c.comment_email), "at": c.creation}
			for c in comments
		],
		"can_edit": role == rules.OWNER,
		"can_work": rules.can_work_on_task(role, user, doc.assignee),
	}


@frappe.whitelist(methods=["POST"])
def save_task(task):
	"""Create (no `name`) or update a task. Owner only. Fields: title,
	description, company, assignee, due_date, priority, board_column, and
	checklist [{label, done}] which replaces the current one."""
	user = frappe.session.user
	tenant, role, _allowed = access.require_office(user, owner=True)
	data = frappe.parse_json(task) if isinstance(task, str) else (task or {})
	if not isinstance(data, dict):
		frappe.throw(_("Invalid task"))

	if data.get("name"):
		doc, _ctx = access.load_task(data["name"], user)
	else:
		doc = frappe.new_doc(TASK)
		doc.tenant = tenant
		doc.board_column = access.columns(tenant)[0].name
	for field in EDITABLE_FIELDS:
		if field in data:
			doc.set(field, data.get(field) or None)
	if "checklist" in data:
		doc.set("checklist", [])
		for item in data.get("checklist") or []:
			if isinstance(item, dict):
				doc.append("checklist", {"label": item.get("label"), "done": 1 if item.get("done") else 0})
	doc.save(ignore_permissions=True)
	return ok(_detail(doc, user, role))


@frappe.whitelist(methods=["POST"])
def delete_task(name):
	user = frappe.session.user
	access.require_office(user, owner=True)
	doc, _ctx = access.load_task(name, user)
	doc.delete(ignore_permissions=True)
	return ok({"deleted": name})


@frappe.whitelist(methods=["POST"])
def set_task_status(name, board_column):
	"""Move a task to another column: the owner, or the task's assignee."""
	user = frappe.session.user
	doc, (_tenant, role, _allowed) = access.load_task(name, user)
	if not rules.can_work_on_task(role, user, doc.assignee):
		frappe.throw(_("Only the owner or the assignee can change this task"), frappe.PermissionError)
	doc.board_column = board_column
	doc.save(ignore_permissions=True)
	return ok(_detail(doc, user, role))


@frappe.whitelist(methods=["POST"])
def set_checklist_item(name, item, done):
	user = frappe.session.user
	doc, (_tenant, role, _allowed) = access.load_task(name, user)
	if not rules.can_work_on_task(role, user, doc.assignee):
		frappe.throw(_("Only the owner or the assignee can change this task"), frappe.PermissionError)
	row = next((r for r in doc.checklist if r.name == item), None)
	if row is None:
		frappe.throw(_("Checklist item not found"), frappe.DoesNotExistError)
	row.done = 1 if frappe.utils.cint(done) else 0
	doc.save(ignore_permissions=True)
	return ok(_detail(doc, user, role))


@frappe.whitelist(methods=["POST"])
def add_task_comment(name, text):
	"""Anyone in the office who can see the task may comment on it."""
	user = frappe.session.user
	doc, (_tenant, role, _allowed) = access.load_task(name, user)
	text = (text or "").strip()
	if not text or len(text) > 2000:
		frappe.throw(_("Write a comment (up to 2000 characters)"))
	doc.add_comment("Comment", frappe.utils.escape_html(text), comment_email=user)
	return ok(_detail(doc, user, role))


@frappe.whitelist(methods=["POST"])
def save_columns(columns):
	"""Replace the board's columns. Owner only. `columns`: [{name?, title,
	is_done}] in display order; a column left out is deleted, which is refused
	while tasks are still in it."""
	user = frappe.session.user
	tenant, _role, _allowed = access.require_office(user, owner=True)
	data = frappe.parse_json(columns) if isinstance(columns, str) else (columns or [])
	if not isinstance(data, list) or not all(isinstance(c, dict) for c in data):
		frappe.throw(_("Invalid columns"))
	problems = rules.column_problems(data)
	if problems:
		frappe.throw(_(COLUMN_ERRORS[problems[0]]))

	existing = {c.name for c in access.columns(tenant)}
	removed = existing - {c.get("name") for c in data if c.get("name")}
	if removed and frappe.db.exists(TASK, {"board_column": ["in", list(removed)]}):
		frappe.throw(_("Move the tasks out of a column before deleting it"))
	kept = set()
	for position, column in enumerate(data):
		name = column.get("name")
		if name:
			if name not in existing:
				frappe.throw(_("Unknown board column"))
			doc = frappe.get_doc(COLUMN, name)
			kept.add(name)
		else:
			doc = frappe.new_doc(COLUMN)
			doc.tenant = tenant
		doc.title = column.get("title")
		doc.is_done = 1 if column.get("is_done") else 0
		doc.column_order = position
		doc.save(ignore_permissions=True)
	for name in existing - kept:
		frappe.delete_doc(COLUMN, name, ignore_permissions=True)
	return ok({"columns": _columns_payload(tenant)})


@frappe.whitelist()
def list_employees():
	"""Who the owner can assign tasks to: themselves and the Active Employees,
	each with the companies they may use."""
	user = frappe.session.user
	tenant, _role, _allowed = access.require_office(user, owner=True)
	owner = access.tenant_owner(tenant)
	people = [{"email": owner, "full_name": get_fullname(owner), "is_owner": True, "companies": None}]
	for email, companies in sorted(access.employees(tenant).items()):
		people.append({"email": email, "full_name": get_fullname(email), "is_owner": False, "companies": companies})
	return ok(people)


@frappe.whitelist(methods=["POST"])
def set_member_type(member, member_type):
	"""Mark a Member of the owner's workspace as an Employee (works in the
	office, can be assigned tasks) or a Client (never sees the board). Owner
	only. The app calls it right after accounting's invite_team_member, and
	from the team list. Open tasks stay assigned until the owner reassigns."""
	user = frappe.session.user
	tenant, _role, _allowed = access.require_office(user, owner=True)
	if member_type not in rules.MEMBER_TYPES:
		frappe.throw(_("Member type must be Employee or Client"))
	if not member or frappe.db.get_value("Member", member, "tenant") != tenant:
		frappe.throw(_("Member not found"), frappe.DoesNotExistError)
	frappe.db.set_value("Member", member, "member_type", member_type)
	return ok({"member": member, "member_type": member_type})


@frappe.whitelist()
def member_types():
	"""{member name: "Employee" | "Client"} for the owner's workspace, to show
	beside accounting's team list (get_team_members does not return the type)."""
	user = frappe.session.user
	tenant, _role, _allowed = access.require_office(user, owner=True)
	rows = frappe.get_all(
		"Member", filters={"tenant": tenant, "status": ["!=", "Removed"]}, fields=["name", "member_type"]
	)
	return ok({row.name: row.member_type or rules.MEMBER_CLIENT for row in rows})


@frappe.whitelist()
def my_office_role():
	"""{"role": "owner" | "employee" | null} in the caller's active workspace.
	Never raises, so the app can ask on every load to decide which office links
	to show (clients and users with no workspace get null)."""
	user = frappe.session.user
	try:
		_tenant, role, _allowed = access.office_context(user)
	except Exception:
		role = None
	return ok({"role": role})
