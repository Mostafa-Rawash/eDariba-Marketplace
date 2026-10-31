"""Office task emails: "a task was assigned to you" and the daily reminder of
tasks due tomorrow or overdue. Queued through frappe.sendmail, so a save never
waits on, or fails because of, the mail server. Emails carry a link into the
app; the task details are shown there after login.
"""
from collections import defaultdict

import frappe
from frappe.utils import add_days, formatdate, get_fullname, getdate, today

from marketplace.office import access, rules

DEFAULT_APP_URL = "https://app.edariba.com"


def app_url(path):
	# Same site_config key as the request emails (inquiries/notifications.py).
	base = (frappe.conf.get("marketplace_app_url") or DEFAULT_APP_URL).rstrip("/")
	return f"{base}{path}"


def _send(recipient, subject, template, args):
	try:
		frappe.sendmail(
			recipients=[recipient],
			subject=subject,
			template=template,
			args=args,
			with_container=True,
			delayed=True,
		)
	except Exception:
		# An email must never roll back the task it is about.
		frappe.log_error(title="Office task email failed", message=frappe.get_traceback())


def _workspace_name(tenant):
	return frappe.db.get_value("Tenant", tenant, "company_name") or ""


def _names(doctype, field, names):
	"""{name: field} for `names`, in one query."""
	names = [n for n in names if n]
	if not names:
		return {}
	return dict(frappe.get_all(doctype, filters={"name": ["in", names]}, fields=["name", field], as_list=True))


def _company_name(company):
	return (frappe.db.get_value("Company", company, "company_name") or company) if company else ""


def task_assigned(task):
	_send(
		task.assignee,
		"مهمة جديدة لك على eDariba",
		"office_task_assigned",
		{
			"assigned_by": get_fullname(frappe.session.user),
			"workspace": _workspace_name(task.tenant),
			"title": task.title,
			"company": _company_name(task.company),
			"due_date": formatdate(task.due_date, "dd MMMM yyyy") if task.due_date else "",
			"url": app_url("/office/tasks"),
		},
	)


def send_due_reminders():
	"""Daily (marketplace hooks.py scheduler_events): one email per assignee listing their
	open tasks due tomorrow, today or earlier, across every office."""
	now = getdate(today())
	# Only what the reminder lists (rules.needs_reminder): open and due
	# tomorrow or earlier. done_at is set when a task is saved into a done
	# column; a column marked done later does not touch the tasks already in
	# it, so those are filtered by column as well.
	rows = frappe.get_all(
		"Office Task",
		filters={
			"assignee": ["is", "set"],
			"due_date": ["<=", add_days(now, 1)],
			"done_at": ["is", "not set"],
		},
		fields=["title", "tenant", "company", "assignee", "due_date", "board_column"],
		order_by="due_date asc",
	)
	done_columns = set(frappe.get_all(
		"Office Task Column",
		filters={"is_done": 1, "name": ["in", list({r.board_column for r in rows})]},
		pluck="name",
	)) if rows else set()
	by_assignee = defaultdict(list)
	people = {}
	for row in rows:
		if row.board_column in done_columns:
			continue
		# Still in the office: its owner or an Active Employee. A suspended or
		# removed employee keeps the assignment until the owner reassigns it,
		# but no longer hears about the office's tasks.
		if row.tenant not in people:
			people[row.tenant] = {access.tenant_owner(row.tenant), *access.employees(row.tenant)}
		if row.assignee in people[row.tenant]:
			by_assignee[row.assignee].append(row)
	if not by_assignee:
		return

	# Display names in two queries for the whole run, not two per task.
	listed = [t for tasks in by_assignee.values() for t in tasks]
	workspaces = _names("Tenant", "company_name", {t.tenant for t in listed})
	companies = _names("Company", "company_name", {t.company for t in listed if t.company})

	for assignee, tasks in by_assignee.items():
		_send(
			assignee,
			"مهام مستحقة على eDariba",
			"office_task_reminder",
			{
				"tasks": [
					{
						"title": t.title,
						"company": (companies.get(t.company) or t.company) if t.company else "",
						"workspace": workspaces.get(t.tenant) or "",
						"due_date": formatdate(t.due_date, "dd MMMM yyyy"),
						"overdue": rules.is_overdue(t.due_date, False, now),
					}
					for t in tasks
				],
				"url": app_url("/office/tasks"),
			},
		)
