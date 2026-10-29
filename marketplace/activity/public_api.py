"""Activity reporting from pages (the WordPress site, later the app).

Routes:
  POST /api/method/marketplace.activity.public_api.track
  gateway: {"resource": "event", "action": "track", "params": {...}}

params:
  event       profile_view | service_view | search_click
  slug        the record's public slug
  entity      accountant | service | project (search_click only; views imply it)
  search_id   search_click only: meta.search_id of the search the result came from
  visitor     optional opaque first-party visitor id (cookie); hashed daily, never stored
  user_agent  optional, for bot filtering when the caller is a server (WordPress)

Nothing the caller sends is trusted as a count: the server decides whether an
event counts (published record, not a bot, not the owner, once per visitor
per day, clicks only on results the search really returned) and rate-limits
per visitor. Always answers {"recorded": bool}; reasons are not disclosed.
"""

import frappe
from frappe.rate_limiter import rate_limit

from marketplace.activity import events
from marketplace.activity import rules as event_rules
from marketplace.shared.responses import ok

VIEW_ENTITY = {event_rules.PROFILE_VIEW: "accountant", event_rules.SERVICE_VIEW: "service"}


def record(event: str, slug: str, entity: str = "", search_id: str = "", visitor: str = "", user_agent: str = ""):
	"""The gateway calls this directly; WordPress forwards the visitor's user
	agent and cookie id."""
	if event not in event_rules.TRACKABLE:
		frappe.throw("Unknown event.", frappe.ValidationError)
	request = getattr(frappe.local, "request", None)
	agent = user_agent or (request.headers.get("User-Agent", "") if request else "")
	if event_rules.is_bot(agent):
		return ok({"recorded": False})

	entity = VIEW_ENTITY.get(event, entity)
	resolved = events.resolve_published(entity, (slug or "").strip())
	if not resolved:
		return ok({"recorded": False})
	doctype, name = resolved

	vhash = events.visitor_hash(visitor)
	if events.over_visitor_limit(vhash) or events.excluded_viewer(doctype, name):
		return ok({"recorded": False})

	if event == event_rules.SEARCH_CLICK:
		return ok({"recorded": events.record_click((search_id or "").strip(), entity, name, vhash)})
	events.record_view(event, doctype, name, vhash)
	return ok({"recorded": True})


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=120, seconds=60)
def track(event: str, slug: str, entity: str = "", search_id: str = "", visitor: str = "", user_agent: str = ""):
	return record(event, slug, entity, search_id, visitor, user_agent)
