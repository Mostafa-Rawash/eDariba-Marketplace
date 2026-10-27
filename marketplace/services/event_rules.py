"""Rules for marketplace activity events (views, searches, clicks).

Pure Python (hashlib/hmac/re only), so they are unit-tested without a site.
services/events.py applies them.

Privacy:
- a visitor is stored only as visitor_hash = HMAC(site secret, day | visitor
  key). The day is part of the input, so the same person gets a new hash
  every day: unique visitors can be counted per day but nobody can be followed
  across days, and no IP, cookie or user id is stored;
- search text is normalised and truncated, and long digit runs (tax ids,
  phone numbers) are masked before anything is stored.
"""

import hashlib
import hmac
import re

PROFILE_VIEW = "profile_view"
SERVICE_VIEW = "service_view"
SEARCH = "search"
SEARCH_CLICK = "search_click"

# Events a page may report through api/public/events.track.
TRACKABLE = (PROFILE_VIEW, SERVICE_VIEW, SEARCH_CLICK)

# entity name used in the API -> DocType
ENTITY_DOCTYPES = {
	"accountant": "Marketplace Profile",
	"service": "Marketplace Service",
	"project": "Marketplace Project",
}

QUERY_MAX_CHARS = 100
SEARCH_REFS_MAX = 50
# How long after a search a click on one of its results still counts.
CLICK_WINDOW_HOURS = 24
# Per visitor, per minute, across all event types.
EVENTS_PER_VISITOR_PER_MINUTE = 30

_BOTS = re.compile(
	r"bot|crawl|spider|slurp|preview|facebookexternalhit|whatsapp|telegram|headless|lighthouse|curl|wget|python-requests",
	re.I,
)
_DIGIT_RUN = re.compile(r"\d{5,}")


def is_bot(user_agent: str | None) -> bool:
	"""Missing user agents count as bots: real browsers always send one."""
	return not user_agent or bool(_BOTS.search(user_agent))


def visitor_hash(secret: str, day: str, visitor_key: str) -> str:
	return hmac.new(secret.encode(), f"{day}|{visitor_key}".encode(), hashlib.sha256).hexdigest()[:32]


def dedupe_key(*parts) -> str:
	"""Stable key for 'this already happened': one profile view per visitor
	per day, one click per search result per visitor."""
	return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:40]


def normalise_query(text: str | None) -> str:
	text = " ".join((text or "").lower().split())
	text = _DIGIT_RUN.sub("#", text)
	return text[:QUERY_MAX_CHARS]


def ref(entity: str, name: str) -> str:
	return f"{entity}:{name}"
