"""Keep account identities out of document reads through /api/resource.

Frappe returns the standard `owner` and `modified_by` fields (user e-mails)
with every document, and they are not covered by permlevels. For Marketplace
Profile, Service and Project, the controllers extend IdentityMaskedDocument,
which calls mask_identity() from apply_fieldlevel_read_permissions; Frappe
runs that before returning a single document from /api/resource. Anyone who is not the record's owner or a
moderator gets those fields, and the profile's `company`, blanked.

Guest has no DocPerm on these DocTypes (removed 2026-10-26): the public site
reads them through api/public/*, whose serializers list the fields a guest may
see (services/serializers.py). List reads by logged-in users through
/api/resource can still ask for `owner`; closing that needs the app to read
the directory through api/public as well (see
STATISTICS_AND_GAMIFICATION_BACKEND_IMPLEMENTATION.md, Security).
"""

import frappe
from frappe.model.document import Document

IDENTITY_FIELDS = ("owner", "modified_by")
EXTRA_FIELDS = {"Marketplace Profile": ("company",)}


def record_user(doc) -> str | None:
	"""The account a marketplace record belongs to."""
	if doc.doctype == "Marketplace Profile":
		return doc.user
	if doc.doctype == "Marketplace Service":
		return frappe.db.get_value("Marketplace Profile", doc.provider, "user")
	if doc.doctype == "Marketplace Project":
		return doc.client
	return None


def mask_identity(doc):
	from marketplace.marketplace.permissions import is_moderator

	user = frappe.session.user
	if is_moderator(user) or (record_user(doc) == user and user != "Guest"):
		return
	for field in IDENTITY_FIELDS + EXTRA_FIELDS.get(doc.doctype, ()):
		doc.set(field, None)


class IdentityMaskedDocument(Document):
	def apply_fieldlevel_read_permissions(self):
		super().apply_fieldlevel_read_permissions()
		mask_identity(self)
