"""Activity collection: views, searches, search impressions and clicks.

Two stores:
- Marketplace Activity: one row per unique daily view (per visitor), per
  search, and per click. Deduped with a unique dedupe_key. Raw rows are
  purged after ACTIVITY_RETENTION_DAYS (purge_old_activity, daily job).
- Marketplace Daily Metric: counters per (day, metric, record), upserted with
  one SQL statement. Kept indefinitely; the statistics read these.

Rules (bots, visitor hashing, query masking) live in services/event_rules.py.
Search writes run in a background job (queue "short"), so a list or search
page never waits on them, and they also work for GET requests, which Frappe
does not commit. Views and clicks are written in the tracking POST itself
(api/public/events.py).
Owner and moderator views are not counted. Nothing here is backfilled:
counting starts when this code is deployed.
"""

import json

import frappe
from frappe.utils import add_days, getdate, now_datetime, nowdate

from marketplace.services import event_rules
from marketplace.services.profile_handle import owner_of_slug

ACTIVITY_RETENTION_DAYS = 90


# ------------------------------------------------------------- identity ---


def _secret() -> str:
	conf = frappe.local.conf or {}
	return conf.get("marketplace_visitor_secret") or conf.get("encryption_key") or conf.get("db_name") or "marketplace"


def visitor_hash(visitor: str | None) -> str:
	"""Hash of who is visiting, rotated daily. Prefers the caller's opaque
	visitor id (a first-party cookie set by the site), then the session user,
	then IP + user agent. None of these is stored."""
	user = frappe.session.user
	if visitor:
		key = f"v:{str(visitor)[:100]}"
	elif user and user != "Guest":
		key = f"u:{user}"
	else:
		request = getattr(frappe.local, "request", None)
		agent = request.headers.get("User-Agent", "") if request else ""
		key = f"ip:{getattr(frappe.local, 'request_ip', '')}|{agent}"
	return event_rules.visitor_hash(_secret(), nowdate(), key)


def over_visitor_limit(vhash: str) -> bool:
	"""At most EVENTS_PER_VISITOR_PER_MINUTE events per visitor hash."""
	key = f"marketplace:events:{vhash}:{now_datetime().strftime('%Y%m%d%H%M')}"
	cache = frappe.cache()
	count = cache.incrby(key, 1)
	if count == 1:
		cache.expire(key, 120)
	return count > event_rules.EVENTS_PER_VISITOR_PER_MINUTE


def excluded_viewer(doctype: str, name: str) -> bool:
	"""Owners looking at their own record and moderators are not counted."""
	from marketplace.marketplace.permissions import is_moderator

	user = frappe.session.user
	if not user or user == "Guest":
		return False
	if is_moderator(user):
		return True
	if doctype == "Marketplace Profile":
		return frappe.db.get_value(doctype, name, "user") == user
	if doctype == "Marketplace Service":
		provider = frappe.db.get_value(doctype, name, "provider")
		return frappe.db.get_value("Marketplace Profile", provider, "user") == user
	return False


# ---------------------------------------------------------------- counters ---


def bump(metric: str, reference_doctype: str | None = None, reference_name: str | None = None, by: int = 1, day=None):
	"""Add `by` to a daily counter, creating it if needed (one statement)."""
	bump_many([(metric, reference_doctype, reference_name)], by=by, day=day)


def bump_many(counters: list[tuple], by: int = 1, day=None):
	"""Add `by` to each (metric, reference_doctype, reference_name) counter
	of the day, in one statement."""
	if not counters:
		return
	day = str(getdate(day or nowdate()))
	now = now_datetime()
	rows, values = [], []
	for metric, dt, dn in counters:
		rows.append("(%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Administrator', 'Administrator', 0, 0)")
		key = event_rules.dedupe_key(day, metric, dt or "", dn or "")
		values += [frappe.generate_hash(length=12), key, metric, day, dt, dn, by, now, now]
	frappe.db.sql(
		f"""
		insert into `tabMarketplace Daily Metric`
			(name, metric_key, metric, metric_date, reference_doctype, reference_name, `count`,
			 creation, modified, owner, modified_by, docstatus, idx)
		values {", ".join(rows)}
		on duplicate key update `count` = `count` + values(`count`), modified = values(modified)
		""",
		values,
	)


def _insert_activity(values: dict) -> bool:
	"""Insert an activity row; False when its dedupe_key already exists."""
	doc = frappe.get_doc({"doctype": "Marketplace Activity", **values})
	try:
		frappe.db.savepoint("mp_activity")
		doc.db_insert()
		return True
	except frappe.DuplicateEntryError:
		frappe.db.rollback(save_point="mp_activity")
		return False


# ------------------------------------------------------------------- views ---


def resolve_published(entity: str, slug: str) -> tuple[str, str] | None:
	"""(doctype, name) of a published record, or None."""
	doctype = event_rules.ENTITY_DOCTYPES.get(entity)
	if not doctype or not slug:
		return None
	name = owner_of_slug(slug) if doctype == "Marketplace Profile" else slug
	if not name or frappe.db.get_value(doctype, name, "publication_status") != "Published":
		return None
	return doctype, name


def record_view(event: str, doctype: str, name: str, vhash: str):
	"""Count a view, and a unique visitor once a day."""
	day = nowdate()
	bump(event, doctype, name)
	_insert_activity(
		{
			"event_type": event,
			"event_date": day,
			"occurred_at": now_datetime(),
			"reference_doctype": doctype,
			"reference_name": name,
			"visitor_hash": vhash,
			"dedupe_key": event_rules.dedupe_key(event, day, doctype, name, vhash),
		}
	)


# ---------------------------------------------------------------- searches ---


def log_search(query: str, entity_types, results: list[tuple[str, str]], total: int) -> str:
	"""Record a search and the impressions of the results it returned.
	`results` are (entity, name) pairs of the returned page. Returns the id
	of the search, which the site passes back with a click (search_id)."""
	search_id = frappe.generate_hash(length=16)
	frappe.enqueue(
		"marketplace.services.events.write_search",
		queue="short",
		search_id=search_id,
		query_text=event_rules.normalise_query(query),
		entity_types=",".join(entity_types or []),
		refs=[event_rules.ref(e, n) for e, n in results][: event_rules.SEARCH_REFS_MAX],
		total=int(total or 0),
		vhash=visitor_hash(None),
	)
	return search_id


def search_meta(query: str, entity_types, results: list[tuple[str, str]], total: int, page: int) -> dict:
	"""For list and search endpoints: log a text search (first page only, so
	paging is not counted as new searches) and return {"search_id": ...} for
	the response meta. A logging failure never breaks the search."""
	if not (query or "").strip() or page != 1:
		return {}
	try:
		return {"search_id": log_search(query, entity_types, results, total)}
	except Exception:
		frappe.log_error(title="Marketplace search logging failed")
		return {}


def write_search(search_id: str, query_text: str, entity_types: str, refs: list[str], total: int, vhash: str):
	doc = frappe.get_doc(
		{
			"doctype": "Marketplace Activity",
			"event_type": event_rules.SEARCH,
			"event_date": nowdate(),
			"occurred_at": now_datetime(),
			"visitor_hash": vhash,
			"query_text": query_text,
			"entity_types": entity_types,
			"result_count": total,
			"result_refs": json.dumps(refs),
		}
	)
	doc.name = search_id
	doc.db_insert()
	counters = [("search", None, None)]
	if not total:
		counters.append(("search_no_result", None, None))
	for item in refs:
		entity, _, name = item.partition(":")
		counters.append(("search_impression", event_rules.ENTITY_DOCTYPES.get(entity), name))
	bump_many(counters)


def record_click(search_id: str, entity: str, name: str, vhash: str) -> bool:
	"""A click counts only for a result the search really returned, within
	CLICK_WINDOW_HOURS, once per visitor."""
	search = frappe.db.get_value(
		"Marketplace Activity", search_id, ["event_type", "occurred_at", "result_refs"], as_dict=True
	)
	if not search or search.event_type != event_rules.SEARCH:
		return False
	if (now_datetime() - search.occurred_at).total_seconds() > event_rules.CLICK_WINDOW_HOURS * 3600:
		return False
	if event_rules.ref(entity, name) not in json.loads(search.result_refs or "[]"):
		return False
	doctype = event_rules.ENTITY_DOCTYPES[entity]
	inserted = _insert_activity(
		{
			"event_type": event_rules.SEARCH_CLICK,
			"event_date": nowdate(),
			"occurred_at": now_datetime(),
			"reference_doctype": doctype,
			"reference_name": name,
			"visitor_hash": vhash,
			"search": search_id,
			"dedupe_key": event_rules.dedupe_key(event_rules.SEARCH_CLICK, search_id, entity, name, vhash),
		}
	)
	if inserted:
		bump(event_rules.SEARCH_CLICK, doctype, name)
	return inserted


# --------------------------------------------------------------- retention ---


def purge_old_activity():
	"""Daily (hooks.scheduler_events): drop raw activity past retention.
	Daily metrics are kept."""
	days = int((frappe.local.conf or {}).get("marketplace_activity_retention_days") or ACTIVITY_RETENTION_DAYS)
	frappe.db.delete("Marketplace Activity", {"event_date": ["<", add_days(nowdate(), -days)]})
