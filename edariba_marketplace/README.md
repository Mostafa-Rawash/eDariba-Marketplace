# edariba_marketplace (Frappe app)

Built **without live bench access**: the `frappe` MCP bridge authenticates
(`ping` succeeds) but every real call (`list_documents`, `get_doctype_schema`,
`call_method`) fails the same way, which the diagnostics report as an auth
error despite API key/secret being present. The actual existing custom
Frappe app name, module layout, and any pre-existing DocTypes on the remote
(Lightsail) site could not be inspected. **App name assumption:**
`edariba_marketplace`, mirroring the WordPress plugin slug
(`plugins/edariba-marketplace`). If a differently-named app already exists
on the live site, move `edariba_marketplace/**` into it instead of running
both.

**Source of truth for the DocTypes**: the WordPress marketplace plugin and
theme templates (`plugins/edariba-marketplace/includes/class-dummy-data-provider.php`,
`themes/edariba-theme/marketplace/*.php`) — every field traces to a specific
template, not invented.

## What's here

- `edariba_marketplace/marketplace/doctype/*` — 8 DocTypes: Profile, Service,
  Project, Proposal, Inquiry, Category, Tag (child), Qualification (child).
- `edariba_marketplace/api/marketplace/*` — public REST endpoints (list/get
  for accountants/services/projects, metadata, unified search, chat).
- `edariba_marketplace/services/marketplace/*` — repository/serializer/filter
  layer, Qdrant client, embedding client, indexing pipeline, deterministic
  intent router (ported from `class-chat-router.php`, not re-derived).
- `postman/eDariba-Marketplace.postman_collection.json` — every endpoint with
  example requests.

## Qdrant collections — one per entity type (2026-10-15)

Originally used one shared `edariba_marketplace` collection with an
`entity_type` payload discriminator (still exists on the instance, unused
now). Switched to a dedicated collection per type on explicit instruction:

| Entity | Collection | Status when found |
|---|---|---|
| accountant | `accountants` | **Already existed** with 20 unrelated real records (name/address/phone/email/rating/feedback schema, integer ids 1–20, no `status` payload key). Reused anyway per explicit decision — query-safe because our search always filters on `status=Published`, which those points don't have, so Qdrant excludes them automatically. A raw `scroll` through this collection shows both datasets mixed. |
| service | `services` | Created fresh (1024-dim, Cosine) — did not exist before. |
| project | `projects` | Created fresh (1024-dim, Cosine) — did not exist before. |

Config: `services/marketplace/config.py:qdrant_collection_for(entity_type)`,
overridable via `QDRANT_COLLECTION_ACCOUNTANTS` / `_SERVICES` / `_PROJECTS`.

A "unified" search across multiple entity types is a fan-out — one Qdrant
`/points/search` per relevant collection, merged by score in
`search_service.py` — Qdrant has no cross-collection query.

## Verified live (not just code-reviewed)

- Embedding API (`EMBEDDING_API_URL`): real key tested → `Authorization:
  Bearer <key>`, body `{"inputs": "<text>"}` (not `"input"`), response is a
  bare `[[1024 floats]]`.
- Full pipeline — embed → Qdrant upsert → search → delete → verify-gone —
  run against all three real collections (`accountants`/`services`/`projects`),
  cleaned up after itself each time.
- Caught and fixed a real bug this way: Qdrant rejects string point IDs
  (`400 not a valid point ID`); `indexing_service._point_id` now uses a
  deterministic `uuid5(doctype:name)`.
- `services/marketplace/intent_router.py`: 5/5 unit tests actually executed
  (`python3 -m unittest ...tests.test_intent_router`), no Frappe needed.

## Not verified (no bench here)

DocType JSON (`python3 -m json.tool`) and every `.py` (`py_compile`) are
syntax-valid, but nothing has gone through `bench migrate` — permissions,
validation hooks, and `doc_events` wiring are reviewed, not executed against
a real database.

## Known gap

A Profile's `service_ids` payload field (if ever reintroduced — see
`indexing_service.build_profile_payload`) is computed only when the Profile
itself is saved; editing one of its Services does not refresh the Profile's
point. Currently harmless since nothing reads `service_ids` in search
filtering, but worth knowing before building on it.
