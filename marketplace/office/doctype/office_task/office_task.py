import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from marketplace.office import access, notifications, rules

# Translated when raised (frappe's _ needs the request's language).
ASSIGNEE_ERRORS = {
	"not_employee": "Tasks can only be assigned to the account owner or an employee",
	"no_company_access": "This employee has no access to the task's company",
}


class OfficeTask(Document):
	"""App users change tasks only through office/api.py, which checks who the
	caller is. This controller keeps the invariants that must hold however the
	task is saved: one office, a column and company of that office, an allowed
	assignee, and done_at following the column."""

	def validate(self):
		self.title = (self.title or "").strip()
		if not self.title or len(self.title) > rules.TASK_TITLE_MAX:
			frappe.throw(_("Task title is required (up to {0} characters)").format(rules.TASK_TITLE_MAX))
		if self.priority not in rules.PRIORITIES:
			self.priority = "Normal"
		if not self.is_new() and self.has_value_changed("tenant"):
			frappe.throw(_("A task cannot move to another account"), frappe.PermissionError)

		column = frappe.db.get_value(access.COLUMN, self.board_column, ["tenant", "is_done"], as_dict=True)
		if not column or column.tenant != self.tenant:
			frappe.throw(_("Unknown board column"))
		# Only when the company is set or changed: accounting's delete_company
		# moves a Company to another tenant, and its tasks must stay workable.
		company_set = self.is_new() or self.has_value_changed("company")
		if self.company and company_set and frappe.db.get_value("Company", self.company, "tenant") != self.tenant:
			frappe.throw(_("You don't have access to this company"), frappe.PermissionError)

		if self.is_new() or self.has_value_changed("assignee") or self.has_value_changed("company"):
			problem = rules.assignee_problem(
				self.assignee, access.tenant_owner(self.tenant), access.employees(self.tenant), self.company)
			if problem:
				frappe.throw(_(ASSIGNEE_ERRORS[problem]))

		if column.is_done and not self.done_at:
			self.done_at = now_datetime()
		elif not column.is_done:
			self.done_at = None

		for row in self.checklist:
			row.label = (row.label or "").strip()[: rules.TASK_TITLE_MAX]
		self.set("checklist", [row for row in self.checklist if row.label])

	def on_update(self):
		if self.assignee and self.has_value_changed("assignee") and self.assignee != frappe.session.user:
			notifications.task_assigned(self)
