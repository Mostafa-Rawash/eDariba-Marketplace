"""Marketplace statistics (logged-in only).

Routes:
  GET /api/method/marketplace.api.stats.provider_stats      ?from_date=&to_date=
  GET /api/method/marketplace.api.stats.profile_completion
  GET /api/method/marketplace.api.stats.admin_stats         ?from_date=&to_date=   (moderators)

Dates are YYYY-MM-DD, inclusive; the default is the last 90 days and a range
may span at most 366 days. A provider only ever gets their own profile's
numbers (the profile comes from the session, never from a parameter). Rates
are null below a minimum sample (min_sample) rather than a misleading 0 or
100%. Formulas: services/stats_formulas.py.
"""

import frappe
from frappe import _

from marketplace.api.common import ok
from marketplace.marketplace.permissions import is_moderator
from marketplace.services import stats


@frappe.whitelist()
def provider_stats(from_date: str | None = None, to_date: str | None = None):
	return ok(stats.provider_stats(frappe.session.user, from_date, to_date))


@frappe.whitelist()
def profile_completion():
	return ok(stats.own_completion(frappe.session.user))


@frappe.whitelist()
def admin_stats(from_date: str | None = None, to_date: str | None = None):
	if not is_moderator():
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	return ok(stats.admin_stats(from_date, to_date))
