"""Public filter/category metadata for the WordPress search UI.

Route:
  GET /api/method/edariba_marketplace.api.public.metadata.get_metadata

Categories come from the managed Marketplace Category doctype (not a
hardcoded list) since that is now a real, editable taxonomy. Governorate and
client_type stay as Select-field option lists pulled from the DocType meta
rather than duplicated here — one source of truth, no drift if the Select
options are ever edited.
"""

import frappe

from edariba_marketplace.api.common import ok

CACHE_KEY = "edariba_marketplace:metadata"
CACHE_TTL_SECONDS = 300


def _select_options(doctype: str, fieldname: str) -> list[str]:
	options = frappe.get_meta(doctype).get_field(fieldname).options or ""
	return [o for o in options.split("\n") if o]


def _build_metadata() -> dict:
	categories = frappe.get_all(
		"Marketplace Category",
		filters={"is_active": 1},
		fields=["title", "slug"],
		order_by="sort_order asc",
		ignore_permissions=True,
	)
	return {
		"categories": categories,
		"governorates": _select_options("Marketplace Profile", "governorate"),
		"client_types": _select_options("Marketplace Project", "client_type"),
		"price_units": _select_options("Marketplace Service", "price_unit"),
	}


@frappe.whitelist(allow_guest=True)
def get_metadata():
	cached = frappe.cache().get_value(CACHE_KEY)
	if cached is not None:
		return ok(cached)
	data = _build_metadata()
	frappe.cache().set_value(CACHE_KEY, data, expires_in_sec=CACHE_TTL_SECONDS)
	return ok(data)


def clear_cache(doc=None, method=None):
	"""doc_events hook target (Marketplace Category on_update/on_trash)."""
	frappe.cache().delete_value(CACHE_KEY)
