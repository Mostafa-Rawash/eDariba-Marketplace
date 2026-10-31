"""Single-endpoint gateway for WordPress, per explicit request (2026-10-15):
one URL instead of several separate whitelisted methods. Read-only except
for event/track (page views and search clicks, checked and deduped by the
server in activity/public_api.py): every write by a person happens in the
logged-in app (inquiries/api.py), never through WordPress.

Route:
  POST /api/method/marketplace.api.gateway.request
  Body: {"resource": "accountant", "action": "list", "params": {...}}

This does NOT duplicate business logic — every (resource, action) pair below
is a direct call into the same functions already built in api/public/
(accountants.py / services.py / projects.py / metadata.py / search.py).
The gateway is purely a router: it validates
(resource, action) against an explicit allowlist, then forwards `params` as
kwargs to the matching function. No dynamic attribute lookup from
client-supplied strings — the dispatch table below is the only thing that
decides what code can run, so a client can never request an arbitrary
Frappe method by name.
"""

import inspect

import frappe

from marketplace.activity import public_api as event_api
from marketplace.freelance import public_api as projects
from marketplace.marketplace.public_api import accountants, metadata, services
from marketplace.search import public_api as search

_DISPATCH = {
	# The one write the gateway forwards: activity reporting. It records
	# nothing the server does not check itself (activity/public_api.py).
	("event", "track"): event_api.record,
	("accountant", "list"): accountants.list_accountants,
	("accountant", "get"): accountants.get_accountant,
	("service", "list"): services.list_services,
	("service", "get"): services.get_service,
	("project", "list"): projects.list_projects,
	("project", "get"): projects.get_project,
	("metadata", "get"): metadata.get_metadata,
	("search", "query"): search.search,
}


@frappe.whitelist(allow_guest=True)
def request(resource: str, action: str, params: dict | None = None):
	key = (resource, action)
	handler = _DISPATCH.get(key)
	if handler is None:
		frappe.throw(f"Unknown resource/action: {resource}/{action}", frappe.ValidationError)

	params = frappe.parse_json(params) if isinstance(params, str) else (params or {})
	if not isinstance(params, dict):
		frappe.throw("params must be an object.")
	_check_params(handler, params, f"{resource}/{action}")

	return handler(**params)


def _check_params(handler, params: dict, label: str) -> None:
	"""Turn a bad `params` into a clear 417 validation error instead of the
	TypeError (500) that calling the handler with it would raise."""
	signature = inspect.signature(handler)
	allowed = set(signature.parameters)
	unknown = sorted(set(params) - allowed)
	if unknown:
		frappe.throw(
			f"Unknown params for {label}: {', '.join(unknown)}. Allowed: {', '.join(sorted(allowed))}.",
			frappe.ValidationError,
		)
	missing = sorted(
		name
		for name, p in signature.parameters.items()
		if p.default is inspect.Parameter.empty and name not in params
	)
	if missing:
		frappe.throw(f"Missing params for {label}: {', '.join(missing)}.", frappe.ValidationError)
