"""Verified by default (services/verification.py), applied to existing rows.

Scope: Marketplace Profiles whose verification_status is Pending or empty
become Verified with verification_method "Automatic". Profiles already
Verified with no method (owners could self-verify before 2026-10-26) are
marked "Automatic" too, since nobody reviewed them. Rejected profiles are not
touched: rejection is a moderator decision.

Safe to re-run: it only changes rows that still match. Skipped entirely when
site_config sets "marketplace_verification_required". Reversible with the
UPDATE in services/verification.py (by verification_method = "Automatic").
Plain UPDATEs, so no controller hooks run and modified is not bumped.
"""

import frappe
from frappe.utils import now_datetime

from marketplace.services import verification


def execute():
	if verification.verification_required():
		return
	frappe.db.sql(
		"""
		update `tabMarketplace Profile`
		set verification_status = 'Verified', verification_method = 'Automatic', verified_at = %s
		where ifnull(verification_status, '') in ('', 'Pending')
		""",
		now_datetime(),
	)
	# The last change is the best available time; nothing better was recorded.
	frappe.db.sql(
		"""
		update `tabMarketplace Profile`
		set verification_method = 'Automatic', verified_at = modified
		where verification_status = 'Verified' and ifnull(verification_method, '') = ''
		"""
	)
