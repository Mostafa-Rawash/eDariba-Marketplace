"""Configuration for external Marketplace integrations (Qdrant, embeddings).

Read from environment variables first, falling back to site_config.json via
frappe.conf — standard Frappe convention for secrets that must not live in
source control. Nothing here is validated at import time: a misconfigured or
absent embedding key must not break DocType CRUD or any endpoint that doesn't
need it. Each client validates its own config lazily, on first real use.
"""

import os

import frappe


def _get(key: str, default: str | None = None) -> str | None:
	# frappe.conf keys are conventionally lowercase; env vars stay as given.
	return os.environ.get(key) or frappe.conf.get(key.lower()) or default


def qdrant_url() -> str:
	url = _get("QDRANT_URL")
	if not url:
		frappe.throw("QDRANT_URL is not configured.")
	return url.rstrip("/")


_ENTITY_COLLECTION_DEFAULTS = {
	"accountant": "accountants",
	"service": "services",
	"project": "projects",
}

_ENTITY_COLLECTION_ENV = {
	"accountant": "QDRANT_COLLECTION_ACCOUNTANTS",
	"service": "QDRANT_COLLECTION_SERVICES",
	"project": "QDRANT_COLLECTION_PROJECTS",
}


def qdrant_collection_for(entity_type: str) -> str:
	"""One collection per entity type, decided explicitly by the user
	(2026-10-15) rather than the single shared "edariba_marketplace"
	collection used earlier. "accountants" already existed on the live
	instance with 20 unrelated real-looking records (different schema: name/
	address/phone/email/rating/feedback, integer ids 1-20, no "status" field)
	— that collision was flagged and the explicit decision was to reuse it
	anyway. It's query-safe (our search always filters on a "status" payload
	key that those older points don't have, so Qdrant's match filter excludes
	them), but a `scroll` through "accountants" will show both datasets mixed
	together. "services" and "projects" were newly created (PUT .../collections/<name>,
	1024-dim Cosine, matching the others) since neither existed before."""
	if entity_type not in _ENTITY_COLLECTION_DEFAULTS:
		frappe.throw(f"Unknown entity_type for Qdrant collection lookup: {entity_type}")
	env_key = _ENTITY_COLLECTION_ENV[entity_type]
	return _get(env_key, _ENTITY_COLLECTION_DEFAULTS[entity_type])


def embedding_api_url() -> str:
	"""Returns the base URL with no trailing slash and no trailing '/embed' —
	callers append '/embed' themselves. Handles both conventions operators
	might set EMBEDDING_API_URL to (the task's own .env example includes
	'/embed' already; the brief's dotenv block does too), so it normalizes
	either input to the same base instead of risking a doubled '/embed/embed'."""
	url = _get("EMBEDDING_API_URL")
	if not url:
		frappe.throw("EMBEDDING_API_URL is not configured.")
	url = url.rstrip("/")
	if url.endswith("/embed"):
		url = url[: -len("/embed")]
	return url


def embedding_api_model() -> str:
	return _get("EMBEDDING_API_MODEL", "bge-m3")


def embedding_api_key() -> str:
	key = _get("EMBEDDING_API_KEY")
	if not key:
		frappe.throw(
			"EMBEDDING_API_KEY is not configured. Set it via an environment "
			"variable or site_config.json on the server — never in source "
			"control. Verified contract (2026-10-14): POST {url}/embed with "
			'header "Authorization: Bearer <key>" and body {"inputs": "<text>"} '
			"returns a bare JSON list of 1024-float vectors."
		)
	return key


def http_timeout_seconds() -> tuple[float, float]:
	"""(connect_timeout, read_timeout) — always bounded, never block forever
	on an external call from inside a web request."""
	return (3.0, 8.0)
