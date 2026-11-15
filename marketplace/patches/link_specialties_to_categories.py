"""Link seeded specialties to their categories.

seed_marketplace_specialties left `category` empty for any specialty whose
Marketplace Category did not exist yet when it ran. This fills in those links
from the same seed mapping, now that the categories exist. It only touches
specialties that still have no category, so a moderator's choice is kept.
Categories that are still missing are skipped; re-running links them later."""

import frappe

from marketplace.marketplace.public_api.metadata import clear_cache
from marketplace.patches.seed_marketplace_specialties import SPECIALTIES


def execute():
	linked_any = False
	for category, titles in SPECIALTIES.items():
		if not frappe.db.exists("Marketplace Category", category):
			continue
		for title in titles:
			if not frappe.db.exists("Marketplace Specialty", title):
				continue
			if frappe.db.get_value("Marketplace Specialty", title, "category"):
				continue
			frappe.db.set_value("Marketplace Specialty", title, "category", category, update_modified=False)
			linked_any = True

	# set_value skips doc events, so the metadata cache hook doesn't fire.
	if linked_any:
		clear_cache()
