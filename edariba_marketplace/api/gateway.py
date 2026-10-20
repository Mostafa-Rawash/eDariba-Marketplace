"""Single-endpoint gateway for WordPress, per explicit request (2026-10-15):
one URL instead of nine separate whitelisted methods.

Route:
  POST /api/method/edariba_marketplace.api.gateway.request
  Body: {"resource": "accountant", "action": "list", "params": {...}}

This does NOT duplicate business logic — every (resource, action) pair below
is a direct call into the same functions already built in api/public/
(accountants.py / services.py / projects.py / metadata.py / search.py /
chat.py / inquiry.py). The gateway is purely a router: it validates
(resource, action) against an explicit allowlist, then forwards `params` as
kwargs to the matching function. No dynamic attribute lookup from
client-supplied strings — the dispatch table below is the only thing that
decides what code can run, so a client can never request an arbitrary
Frappe method by name.
"""

import frappe

from edariba_marketplace.api.public import accountants, chat, inquiry, metadata, projects, search, services

_DISPATCH = {
	("accountant", "list"): accountants.list_accountants,
	("accountant", "get"): accountants.get_accountant,
	("service", "list"): services.list_services,
	("service", "get"): services.get_service,
	("project", "list"): projects.list_projects,
	("project", "get"): projects.get_project,
	("metadata", "get"): metadata.get_metadata,
	("search", "query"): search.search,
	("chat", "discover"): chat.discover,
	("inquiry", "submit"): inquiry.submit_inquiry,
}


@frappe.whitelist(allow_guest=True)
def request(resource: str, action: str, params: dict | None = None):
	key = (resource, action)
	handler = _DISPATCH.get(key)
	if handler is None:
		frappe.throw(f"Unknown resource/action: {resource}/{action}", frappe.ValidationError)

	params = params or {}
	if not isinstance(params, dict):
		frappe.throw("params must be an object.")

	return handler(**params)
