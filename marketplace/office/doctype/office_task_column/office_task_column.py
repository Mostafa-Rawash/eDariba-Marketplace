import frappe
from frappe import _
from frappe.model.document import Document

from marketplace.office import rules


class OfficeTaskColumn(Document):
	def validate(self):
		self.title = (self.title or "").strip()
		if not self.title or len(self.title) > rules.COLUMN_TITLE_MAX:
			frappe.throw(_("Column title is required (up to {0} characters)").format(rules.COLUMN_TITLE_MAX))
		if not self.is_new() and self.has_value_changed("tenant"):
			frappe.throw(_("A column cannot move to another account"), frappe.PermissionError)

	def on_trash(self):
		if frappe.db.exists("Office Task", {"board_column": self.name}):
			frappe.throw(_("Move the tasks out of this column before deleting it"))
