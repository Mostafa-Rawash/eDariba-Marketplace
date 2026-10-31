"""Move DocTypes from the single "Marketplace" module into the domain modules
(modules.txt, 2026-10-29).

Runs before the schema sync: Frappe finds a DocType's controller through the
module stored on its DocType record, and the old folders
(marketplace/marketplace/doctype/<name>) no longer exist. The sync would set
the module from the JSON anyway; doing it here first means nothing loads a
controller from the old path in between. Tables and data are untouched.

Safe to re-run: it creates missing Module Defs and only updates DocTypes
whose module still differs. Plain UPDATEs, so no controller hooks run.
"""

import frappe

APP = "marketplace"

DOCTYPE_MODULES = {
	"Marketplace Inquiry": "Inquiries",
	"Marketplace Project": "Freelance",
	"Marketplace Proposal": "Freelance",
	"Marketplace Activity": "Activity",
	"Marketplace Daily Metric": "Activity",
	"Marketplace Points Entry": "Gamification",
	"Marketplace Achievement": "Gamification",
	"Marketplace User Achievement": "Gamification",
}
# Modules whose DocTypes are new (nothing to move), created up front too.
NEW_MODULES = ("Office",)


def execute():
	for module in sorted(set(DOCTYPE_MODULES.values()) | set(NEW_MODULES)):
		if not frappe.db.exists("Module Def", module):
			frappe.get_doc({"doctype": "Module Def", "module_name": module, "app_name": APP}).insert(
				ignore_permissions=True
			)
	for doctype, module in DOCTYPE_MODULES.items():
		frappe.db.sql(
			"update `tabDocType` set module = %s where name = %s and module != %s", (module, doctype, module)
		)
	frappe.clear_cache()
