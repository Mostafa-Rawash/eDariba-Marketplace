"""The signed-in user's points and achievements (read-only).

Routes:
  GET /api/method/marketplace.api.gamification.my_points        ?page=&page_size=
  GET /api/method/marketplace.api.gamification.my_achievements

There is no endpoint that awards or changes points: they are created only by
server-side hooks (services/gamification.py). The user always comes from the
session.
"""

import frappe

from marketplace.api.common import ok
from marketplace.services import gamification
from marketplace.services.filters import clamp_page, clamp_page_size


@frappe.whitelist()
def my_points(page: int = 1, page_size: int = 20):
	user = frappe.session.user
	page = clamp_page(page)
	page_size = clamp_page_size(page_size)
	filters = {"user": user}
	rows = frappe.get_all(
		gamification.LEDGER,
		filters=filters,
		fields=["points", "event_type", "reference_doctype", "reference_name", "awarded_at"],
		order_by="awarded_at desc",
		limit_start=(page - 1) * page_size,
		limit_page_length=page_size,
		ignore_permissions=True,
	)
	total_entries = frappe.db.count(gamification.LEDGER, filters)
	return ok(rows, page=page, page_size=page_size, total=total_entries, meta={"balance": gamification.points_balance(user)})


@frappe.whitelist()
def my_achievements():
	return ok(gamification.achievements_for(frappe.session.user))
