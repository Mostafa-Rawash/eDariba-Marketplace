# edariba_marketplace (Frappe app)

Accountant directory, services marketplace, and client → accountant requests
for eDariba. Installed beside `accounting` on the same Frappe site
(server.edariba.com), so the app at app.edariba.com reaches it with the
user's existing session. It does not change any `accounting` code.

**Source of truth for the DocTypes**: the WordPress marketplace plugin and
theme templates (`plugins/edariba-marketplace/includes/class-dummy-data-provider.php`,
`themes/edariba-theme/marketplace/*.php`).

## Layout

```
pyproject.toml            packaging (bench get-app / pip install -e)
docs/                     INTEGRATION_AUDIT.md, DOCTYPES.md, STITCH_UI_PROMPTS.md
postman/                  every endpoint with example requests
edariba_marketplace/
  hooks.py  patches.txt  modules.txt
  fixtures/role.json      the Marketplace Moderator role
  marketplace/doctype/    8 DocTypes: Profile, Service, Project, Proposal,
                          Inquiry (a "request"), Category, Tag, Qualification
  marketplace/permissions.py   row-level read rules
  api/public/             Guest, read-only: accountants, services, projects,
                          metadata, search
  api/gateway.py          one read-only URL for WordPress
  api/workspace.py        logged-in request flow for app.edariba.com
  services/               repository, serializers, filters, Qdrant/embedding
                          clients, indexing, intent router, request rules,
                          partner badge, notifications
  templates/emails/       request emails (Arabic, RTL)
```

## Design decisions (agreed 2026-10-20)

- **Roles come from records, not Frappe roles.** A user is a provider when
  they own a Marketplace Profile (one per user). The profile has two
  switches: `offers_services` (directory, services, receives requests) and
  `accepts_projects` (sends proposals on posted projects). Any logged-in user
  can send a request. Workspace roles (Owner / Member / reseller) stay in
  `accounting` and are untouched; one person can hold any mix of both.
- **Only one role is added:** `Marketplace Moderator` (fixture), for staff who
  verify profiles in Desk. Normal users hold no DocPerm on any Marketplace
  DocType, so `/api/resource` is closed to them; every write goes through
  `api/workspace.py`, which takes the user from the session and checks
  ownership itself.
- **Requests need login** (J3). The old guest `inquiry.submit_inquiry`
  endpoint and the Guest create permission are gone; a guest
  `POST /api/resource/Marketplace Inquiry` is refused.
- **Anyone can apply to be listed; a moderator verifies** before a profile
  can be published. Profiles whose owner has an active Partner (reseller)
  plan show an `is_partner` badge (J4 = C). `services/partner.py` is the only
  place that reads accounting data, read-only, and returns "no badge" on any
  failure.
- **Chat discovery is merged into search**: `search.search(auto_intent=1)`.
- Everyone still goes through ETA onboarding in the app (J2); nothing here
  changes that.

## Request flow (`api/workspace.py`)

| Function | Who | What |
|---|---|---|
| `submit_request(recipient, details, inquiry_type?, related_service?, phone?)` | client | Recipient must be Published, Verified, offering services, and not yourself; service must be theirs; one open request per accountant; 10 per hour per user. Emails the accountant. |
| `list_requests(box="sent"\|"received", status?, page?)` | both | Requests you sent / requests to your profile |
| `get_request(name)` | both | Detail, your `role`, `next_statuses`, `can_respond`. Non-parties get "not found". |
| `respond_request(name, message)` | provider | Writes the reply, sets Responded, emails the client |
| `set_request_status(name, status)` | both | Per `services/request_rules.py` |

Statuses: `New → Responded → Accepted → Closed`; the provider can Decline
while New/Responded; the requester can Cancel while New/Responded; either
side closes an Accepted request. Emails contain only a name and a link to
`{marketplace_app_url}/marketplace/requests/<id>` (site_config key, default
`https://app.edariba.com`).

## Qdrant collections — one per entity type (2026-10-15)

Originally used one shared `edariba_marketplace` collection with an
`entity_type` payload discriminator (still exists on the instance, unused
now). Switched to a dedicated collection per type on explicit instruction:

| Entity | Collection | Status when found |
|---|---|---|
| accountant | `accountants` | **Already existed** with 20 unrelated real records (name/address/phone/email/rating/feedback schema, integer ids 1–20, no `status` payload key). Reused anyway per explicit decision — query-safe because our search always filters on `status=Published`, which those points don't have, so Qdrant excludes them automatically. A raw `scroll` through this collection shows both datasets mixed. |
| service | `services` | Created fresh (1024-dim, Cosine) — did not exist before. |
| project | `projects` | Created fresh (1024-dim, Cosine) — did not exist before. |

Config: `services/config.py:qdrant_collection_for(entity_type)`,
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
- Unit tests that need no Frappe (run from the repo root):
  `python -m unittest edariba_marketplace.services.tests.test_intent_router edariba_marketplace.services.tests.test_request_rules`

## Not verified (no bench here)

DocType JSON (`python3 -m json.tool`) and every `.py` (`py_compile`) are
syntax-valid, but nothing has gone through `bench migrate` — permissions,
validation hooks, and `doc_events` wiring are reviewed, not executed against
a real database.

## Known gaps

- No self-service profile/service editing yet (Phase B: `get/save_my_profile`,
  `list/save_my_service`). Until then a moderator creates profiles in Desk.
- The partner badge is shown but does not rank partners higher yet.
- Project and Proposal have no app API yet; they are reachable only in Desk.
- A status change made by the requester (Cancel, Close) sends no email.
- `filters.category` from `auto_intent` is reported in `meta` but not applied
  as a Qdrant filter (the accountant payload has no category).
- Search revalidates hits by slug (`search_service._PUBLIC_LOOKUP`); editing a
  slug drops that record from search until it is renamed to match.
- A Profile's `service_ids` payload field (if ever reintroduced — see
`indexing_service.build_profile_payload`) is computed only when the Profile
itself is saved; editing one of its Services does not refresh the Profile's
point. Currently harmless since nothing reads `service_ids` in search
filtering, but worth knowing before building on it.

## Deploy (server.edariba.com)

Not deployed yet. The server runs Docker Compose project **`edariba`**
(`~/gitops/frappe-v16.yml`, always pass `--project-name edariba`). `accounting`
is a host checkout bind-mounted into seven services; this app is added the
same way. The image has no copy of this app, so after the editable install
the backend container is committed as a new image tag, so the install
survives container re-creation.

```bash
ssh eDariba-Frappe

# 0. Backups
docker exec edariba-backend-1 bench --site server.edariba.com backup
cp ~/gitops/frappe-v16.yml ~/gitops/frappe-v16.yml.bak-$(date +%Y%m%d)

# 1. Code (the folder name must equal the app name)
git clone -b <branch> https://github.com/Mostafa-Rawash/eDariba-Marketplace ~/edariba-apps/edariba_marketplace

# 2. Mount it into the same 7 services that mount accounting
#    (backend, configurator, frontend, queue-long, queue-short, scheduler, websocket):
#      - type: bind
#        source: /home/ubuntu/edariba-apps/edariba_marketplace
#        target: /home/frappe/frappe-bench/apps/edariba_marketplace
nano ~/gitops/frappe-v16.yml
docker compose --project-name edariba -f ~/gitops/frappe-v16.yml up -d

# 3. Install the Python package once, then freeze it into a new image tag
docker exec edariba-backend-1 /home/frappe/frappe-bench/env/bin/pip install -e /home/frappe/frappe-bench/apps/edariba_marketplace
docker commit edariba-backend-1 frappe:16-accounting-890d5fc-r3
#    In frappe-v16.yml replace every image frappe:16-accounting-890d5fc-r2 with -r3, then:
docker compose --project-name edariba -f ~/gitops/frappe-v16.yml up -d

# 4. Register and install on the site
docker exec edariba-backend-1 bash -c 'cd /home/frappe/frappe-bench && grep -qx edariba_marketplace sites/apps.txt || echo edariba_marketplace >> sites/apps.txt'
docker exec edariba-backend-1 bench --site server.edariba.com install-app edariba_marketplace
docker exec edariba-backend-1 bench --site server.edariba.com migrate

# 5. Config (values from the team password store, never from git)
docker exec edariba-backend-1 bench --site server.edariba.com set-config qdrant_url "http://84.235.250.108:9080"
docker exec edariba-backend-1 bench --site server.edariba.com set-config embedding_api_url "http://44.194.201.67:3778/embed"
docker exec edariba-backend-1 bench --site server.edariba.com set-config embedding_api_key "<key>"
docker exec edariba-backend-1 bench --site server.edariba.com set-config marketplace_app_url "https://app.edariba.com"

# 6. Restart
docker restart edariba-backend-1 edariba-frontend-1 edariba-websocket-1 edariba-scheduler-1 edariba-queue-short-1 edariba-queue-long-1
```

Then give staff the **Marketplace Moderator** role in Desk.

**Check after deploy**
- `GET https://server.edariba.com/api/method/edariba_marketplace.api.public.metadata.get_metadata` → `success: true`.
- As a guest, `POST /api/resource/Marketplace Inquiry` → 403.
- Logged in: `workspace.list_requests` → empty list, not an error.

**Later updates**: `cd ~/edariba-apps/edariba_marketplace && git pull`, then
`migrate` and the restart in step 6.

**Rollback** (order matters: the site breaks if the code disappears while the
app is still installed): first
`bench --site server.edariba.com uninstall-app edariba_marketplace --yes`
(drops the marketplace tables), then remove `edariba_marketplace` from
`sites/apps.txt`, then put back the compose backup (r2 image, no mount) and
`up -d`. The step 0 database backup is the fallback if uninstall fails.

**WordPress**: the gateway URL is now
`/api/method/edariba_marketplace.api.gateway.request`; update
`class-frappe-client.php` and set `EDARIBA_FRAPPE_API_URL` in wp-config.php.
