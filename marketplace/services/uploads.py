"""Image uploads for the provider endpoints.

The app sends avatars and service thumbnails as data URLs inside the save
request. This stores them as public File records (they are shown on the
public directory) and returns the file URL for the Attach Image field.
"""

import frappe
from frappe import _

from marketplace.services.provider_rules import ImageError, decode_image


def resolve_image(value, current: str | None, label: str) -> str | None:
	"""The URL to store for an Attach Image field.

	- empty / None: no image;
	- the field's current URL: unchanged;
	- a data URL: stored as a new public File;
	- anything else (a foreign URL, another user's file path): refused, so a
	  user cannot point their listing at arbitrary content.
	"""
	value = (value or "").strip()
	if not value:
		return None
	if current and value == current:
		return current
	if not value.startswith("data:"):
		frappe.throw(_("Upload the {0} as an image file.").format(label))
	try:
		extension, content = decode_image(value)
	except ImageError as exc:
		frappe.throw(_(str(exc)))
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"marketplace-{frappe.generate_hash(length=10)}.{extension}",
			"content": content,
			"is_private": 0,
		}
	)
	file_doc.insert(ignore_permissions=True)
	return file_doc.file_url
