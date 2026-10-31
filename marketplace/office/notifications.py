"""Office task emails: "a task was assigned to you" and the daily reminder of
tasks due tomorrow or overdue. Queued through frappe.sendmail, so a save never
waits on, or fails because of, the mail server. Emails carry a link into the
app; the task details are shown there after login.
"""
from collections import defaultdict

import frappe
from frappe.utils import formatdate, get_fullname, getdate, today

from marketplace.office import rules

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
	done_columns = set(frappe.get_all("Office Task Column", filters={"is_done": 1}, pluck="name"))
	rows = frappe.get_all(
		"Office Task",
		filters={"assignee": ["is", "set"], "due_date": ["is", "set"], "done_at": ["is", "not set"]},
		fields=["title", "tenant", "company", "assignee", "due_date", "board_column"],
		order_by="due_date asc",
	)
	now = getdate(today())
	by_assignee = defaultdict(list)
	for row in rows:
		done = row.board_column in done_columns
		if rules.needs_reminder(row.due_date, done, now):
			by_assignee[row.assignee].append(row)

	for assignee, tasks in by_assignee.items():
		_send(
			assignee,
			"مهام مستحقة على eDariba",
			"office_task_reminder",
			{
				"tasks": [
					{
						"title": t.title,
						"company": _company_name(t.company),
						"workspace": _workspace_name(t.tenant),
						"due_date": formatdate(t.due_date, "dd MMMM yyyy"),
						"overdue": rules.is_overdue(t.due_date, False, now),
					}
					for t in tasks
				],
				"url": app_url("/office/tasks"),
			},
		)
