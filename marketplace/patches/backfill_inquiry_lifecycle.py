"""Lifecycle timestamps for requests created before they were recorded.

Marketplace Inquiry tracks changes (track_changes = 1), so every save left a
Version row listing what changed. For each request with an empty field this
reads its Versions, oldest first, and takes the time of:
- first_responded_at: the first save that set a reply, or moved the status
  from New to Responded, Accepted or Declined;
- accepted_at / declined_at / closed_at / cancelled_at: the first save that
  moved the status there.

Only empty fields are filled, so it is safe to re-run. A request whose
history does not show the event keeps an empty field: nothing is guessed
(responded_at is not copied, because reply edits overwrote it). closed_by is
not in the history and stays empty for old requests.
"""

import json

from marketplace.inquiries.rules import ANSWER_STATUSES
from marketplace.inquiries.rules import TIMESTAMP_FIELDS as STATUS_FIELDS
ALL_FIELDS = ["first_responded_at", *STATUS_FIELDS.values()]


def first_times(versions: list[dict]) -> dict:
	"""{field: time} from Version rows ({creation, data}), oldest first. Pure."""
	found: dict = {}
	for version in versions:
		try:
			changed = (json.loads(version["data"] or "{}") or {}).get("changed") or []
		except (TypeError, ValueError):
			continue
		for row in changed:
			if not isinstance(row, (list, tuple)) or len(row) < 3:
				continue
			field, old, new = row[0], row[1], row[2]
			if field == "response" and new and not old:
				found.setdefault("first_responded_at", version["creation"])
			if field == "status":
				if old == "New" and new in ANSWER_STATUSES:
					found.setdefault("first_responded_at", version["creation"])
				if new in STATUS_FIELDS:
					found.setdefault(STATUS_FIELDS[new], version["creation"])
	return found


def execute():
	import frappe

	or_filters = [[field, "is", "not set"] for field in ALL_FIELDS]
	rows = frappe.get_all(
		"Marketplace Inquiry",
		filters={"status": ["!=", "New"]},
		or_filters=or_filters,
		fields=["name", *ALL_FIELDS],
	)
	for row in rows:
		versions = frappe.get_all(
			"Version",
			filters={"ref_doctype": "Marketplace Inquiry", "docname": row.name},
			fields=["creation", "data"],
			order_by="creation asc",
		)
		updates = {f: t for f, t in first_times(versions).items() if not row.get(f)}
		if updates:
			frappe.db.set_value("Marketplace Inquiry", row.name, updates, update_modified=False)
