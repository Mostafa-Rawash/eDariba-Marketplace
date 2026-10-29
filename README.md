# marketplace (Frappe app)

Accountant directory, services marketplace, and client → accountant requests
for eDariba. Installed beside `accounting` on the same Frappe site
(server.edariba.com), so the app at app.edariba.com reaches it with the
user's existing session. It does not change any `accounting` code.

**Building the app screens or the WordPress pages?** Start with
[docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md).

**Source of truth for the DocTypes**: the WordPress marketplace plugin and
theme templates (`plugins/edariba-marketplace/includes/class-dummy-data-provider.php`,
`themes/edariba-theme/marketplace/*.php`).

## Layout

The app is split into domain modules (2026-10-29). Each module owns its
DocTypes, rules, services and endpoints; `hooks.py` is the only place they are
wired together. A module reads another module's data or calls its public
functions, but never writes another module's DocTypes.

```
pyproject.toml            packaging (bench get-app / pip install -e)
docs/                     DEVELOPER_GUIDE.md, INTEGRATION_AUDIT.md, DOCTYPES.md, STITCH_UI_PROMPTS.md
postman/                  every endpoint with example requests
marketplace/
  hooks.py  patches.txt  modules.txt
  fixtures/role.json      the Marketplace Moderator role

  marketplace/            Frappe module "Marketplace": the directory core
    doctype/              Profile, Service, Category, Tag, Qualification, Specialty
    permissions.py        row-level rules for Profile and Service
    repository.py  serializers.py  partner.py  privacy.py
    profile_handle.py  profile_completion.py  verification.py
    public_api/           Guest reads: accountants, services, metadata
  inquiries/              Frappe module "Inquiries": client -> accountant requests
    doctype/              Inquiry
    permissions.py  rules.py (status table)  notifications.py (emails)
    api.py                logged-in request flow (was api/workspace.py)
  freelance/              Frappe module "Freelance": projects and proposals
    doctype/              Project, Proposal
    permissions.py  rules.py (proposal status table)
    api.py                proposal actions;  public_api.py  Guest project reads
  activity/               Frappe module "Activity": views, searches, clicks
    doctype/              Activity (raw, 90 days), Daily Metric
    rules.py  events.py   public_api.py  the tracking endpoint
  gamification/           Frappe module "Gamification": points and achievements
    doctype/              Points Entry (ledger), Achievement, User Achievement
    rules.py  service.py  api.py (my_points, my_achievements)
  search/                 no DocTypes: Qdrant + embedding clients, indexing,
                          intent router, semantic search;  public_api.py
  stats/                  no DocTypes: provider/admin read models;  api.py
  shared/                 responses.py (envelope), filters.py, permissions.py
                          (is_moderator, published_condition)
  api/                    the published URLs, kept stable: gateway.py (WordPress)
                          plus re-exports of every endpoint that used to live here
  patches/                data patches (split_domain_modules moves the DocTypes)
  templates/emails/       request emails (Arabic, RTL)
```

**Dependency rules.**

- `shared/` depends on nothing in the app.
- The `marketplace/` core logic depends only on `shared/`, with two
  exceptions:
  - one lazy call into `search/` re-indexes a profile when its handle changes;
  - its public list endpoints log searches through `activity.events`.
- Every other module may read the core.
- `stats/` only reads, from every module.
- `search/` and `gamification/` react to other modules' records through
  `doc_events` in `hooks.py`. The owners never import them, so either can be
  switched off or moved into its own app without touching them.

**URLs did not change.** Clients keep calling `marketplace.api.gateway.request`,
`marketplace.api.workspace.*`, `marketplace.api.public.*`, and so on. Those
modules re-export the functions from their new homes, and Frappe resolves
both paths to the same whitelisted function. New endpoints go in their module
and get a re-export in `api/` only if a client needs a stable path. The one
exception is the manual admin sweep, which is now
`marketplace.search.indexing_service.reconcile`; the Postman collection is
updated.

**Migrating a site.** The pre-model-sync patch `split_domain_modules`
creates the four Module Defs and points the moved DocTypes at their new
modules before the schema sync. Tables and data don't change.

## Design decisions (agreed 2026-10-20)

- **Roles come from records, not Frappe roles.** A user is a provider when
  they own a Marketplace Profile (one per user). The profile has two
  switches: `offers_services` (directory, services, receives requests) and
  `accepts_projects` (sends proposals on posted projects). Any logged-in user
  can send a request. Workspace roles (Owner / Member / reseller) stay in
  `accounting` and are untouched; one person can hold any mix of both.
- **Only one role is added:** `Marketplace Moderator` (fixture), for the
  sales and customer-support team (see "Roles" below). Normal users hold no DocPerm on any Marketplace
  DocType, so `/api/resource` is closed to them; every write goes through
  `inquiries/api.py`, which takes the user from the session and checks
  ownership itself.
- **Public reads stay open for SEO, private fields are hidden.** Guest keeps
  read on published Profiles, Services and Projects, but the fields that
  identify a person sit at permlevel 1, which Guests never receive (in
  `/api/resource` lists or single reads): Profile `user` and
  `verification_status`, Project `client`. Only System Manager
  (read and write) and Marketplace Moderator (read) have level-1 access. The public API serializers never
  returned these fields anyway.
- **Requests need login** (J3). The old guest `inquiry.submit_inquiry`
  endpoint and the Guest create permission are gone; a guest
  `POST /api/resource/Marketplace Inquiry` is refused.
- **Anyone can apply to be listed.** Verification is bypassed for now
  (`marketplace/verification.py`); a verifier role comes with that feature. Profiles whose owner has an active Partner (reseller)
  plan show an `is_partner` badge (J4 = C). `marketplace/partner.py` is the only
  place that reads accounting data, read-only, and returns "no badge" on any
  failure.
- **Chat discovery is merged into search**: `search.search(auto_intent=1)`.
- Everyone still goes through ETA onboarding in the app (J2); nothing here
  changes that.

## Roles (2026-10-29)

| Role | Who | Can |
|---|---|---|
| System Manager | eDariba admins | everything, including editing any listing and verification |
| Invoicing Owner (from `accounting`) | every app user: accountants and business owners | their own records only; being a provider or a client comes from their records |
| Marketplace Moderator | sales / customer support | read every profile, service, project, proposal and request (including contact details and the reply history); end an abandoned request or project with a reason |
| Guest | WordPress visitors | published listings, through `marketplace.api.gateway.request` only |

In code, `shared/permissions.py` keeps the two questions apart:
`is_moderator()` (may see everything: System Manager and Moderator) and
`can_edit_any()` (may change records they don't own: System Manager only).

Support never edits the request text or the reply. It never accepts or
responds. Its actions:

- `support_set_request_status(name, status, reason)` (`inquiries/api.py`):
  - New/Responded → Declined, when the accountant disappeared;
  - New/Responded → Cancelled, when the client disappeared or the request
    was wrong;
  - Accepted → Closed.

  The reason (10–500 characters) is stored in `support_note` and logged as a
  comment, and both parties are emailed. A support decline does not count
  as the accountant's first response, and a support close earns no points.
- `support_close_project(name, reason)` (`freelance/api.py`): closes a
  Published project whose client disappeared and rejects its active
  proposals.
- `get_request` returns `role: "support"` to staff, with both sides'
  contact details and `reply_history` (every version of the reply, from
  Frappe's Version log).

## Request flow (`inquiries/api.py`, URL `marketplace.api.workspace.*`)

| Function | Who | What |
|---|---|---|
| `submit_request(recipient, details, inquiry_type?, related_service?, phone?)` | client | Recipient must be Published, Verified, offering services, and not yourself; service must be theirs; one open request per accountant; 10 per hour per user. Emails the accountant. |
| `list_requests(box="sent"\|"received", status?, page?)` | both | Requests you sent / requests to your profile |
| `get_request(name)` | both | Detail, your `role`, `next_statuses`, `can_respond`. Non-parties get "not found". |
| `respond_request(name, message)` | provider | Writes or edits the reply, sets Responded, emails the client each time |
| `set_request_status(name, status)` | both | Per `inquiries/rules.py` |

Statuses: `New → Responded → Accepted → Closed`; the provider can Decline
while New/Responded; the requester can Cancel while New/Responded; either
side closes an Accepted request. Every change emails the other side (the
requester's cancel/close goes to the provider; replies, reply edits and the
provider's status changes go to the requester); nobody is emailed about
their own change. Two submits by the same user are serialized by a row lock
on their User record. Emails contain only a name and a link to
`{marketplace_app_url}/marketplace/requests/<id>` (site_config key, default
`https://app.edariba.com`).

## Qdrant collections — one per entity type, prefixed `marketplace_` (2026-10-20)

| Entity | Collection |
|---|---|
| accountant | `marketplace_accountants` |
| service | `marketplace_services` |
| project | `marketplace_projects` |

All 1024-dim, Cosine; created at deploy (see "Deploy"). The prefix keeps this
app's points apart from everything else on the shared Qdrant instance.

History: first one shared `edariba_marketplace` collection, then (2026-10-15)
`accountants` / `services` / `projects`, where `accountants` also held 20
unrelated records. On 2026-10-20 none of those held marketplace data
(`services` and `projects` were empty); the app no longer uses them, and they
can be deleted once nobody else needs them.

Config: `search/config.py:qdrant_collection_for(entity_type)`,
overridable via `QDRANT_COLLECTION_ACCOUNTANTS` / `_SERVICES` / `_PROJECTS`.

A "unified" search across multiple entity types is a fan-out — one Qdrant
`/points/search` per relevant collection, merged by score in
`search_service.py` — Qdrant has no cross-collection query.

## Verified live (not just code-reviewed)

- Embedding API (`EMBEDDING_API_URL`): real key tested → `Authorization:
  Bearer <key>`, body `{"inputs": "<text>"}` (not `"input"`), response is a
  bare `[[1024 floats]]`.
- Full pipeline — embed → Qdrant upsert → search → delete → verify-gone —
  run against the earlier collections (`accountants`/`services`/`projects`)
  on 2026-10-15, cleaned up after itself each time. Not yet re-run against
  the `marketplace_*` names.
- Caught and fixed a real bug this way: Qdrant rejects string point IDs
  (`400 not a valid point ID`); `indexing_service._point_id` now uses a
  deterministic `uuid5(doctype:name)`.
- Unit tests that need no Frappe (run from the repo root):
  `python -m unittest discover -s marketplace -t . -p "test_*rules.py"` plus
  `marketplace.search.tests.test_intent_router`, `marketplace.stats.tests.test_stats_formulas`,
  `marketplace.marketplace.tests.test_profile_completion`, `marketplace.marketplace.tests.test_verification`,
  `marketplace.inquiries.tests.test_inquiry_backfill` (71 tests, no Frappe needed)

## Not verified (no bench here)

DocType JSON (`python3 -m json.tool`) and every `.py` (`py_compile`) are
syntax-valid, but nothing has gone through `bench migrate` — permissions,
validation hooks, and `doc_events` wiring are reviewed, not executed against
a real database.

## Known gaps

- No self-service profile/service editing yet (Phase B: `get/save_my_profile`,
  `list/save_my_service`). Until then a System Manager creates profiles in Desk.
- The partner badge is shown but does not rank partners higher yet.
- Project and Proposal have no app API yet; they are reachable only in Desk.
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

**Installed 2026-10-20** from `main` at `8dbfc44`. The server runs Docker
Compose project **`edariba`** (`~/gitops/frappe-v16.yml`, always pass
`--project-name edariba`). Like `accounting`, the app is a host checkout,
`~/edariba-apps/marketplace`, bind-mounted into the seven app services
(backend, configurator, frontend, queue-long, queue-short, scheduler,
websocket). Its editable pip install is baked into image
`frappe:16-accounting-890d5fc-r3` (= r2 + `pip install -e apps/marketplace`),
so it survives container re-creation. The configurator rewrites
`sites/apps.txt` from `apps/` on every start, so the mount alone registers it.

What was run, for reference or a rebuild:

```bash
ssh eDariba-Frappe

# 0. Backups
docker exec edariba-backend-1 bench --site server.edariba.com backup
cp ~/gitops/frappe-v16.yml ~/gitops/frappe-v16.yml.bak-<date>-pre-marketplace

# 1. Code (the folder name must equal the app name)
git clone https://github.com/Mostafa-Rawash/eDariba-Marketplace ~/edariba-apps/marketplace

# 2. Image r3 = r2 + the editable install, built in a throwaway container
docker run --name mp-build --user frappe --entrypoint bash   -v /home/ubuntu/edariba-apps/marketplace:/home/frappe/frappe-bench/apps/marketplace   frappe:16-accounting-890d5fc-r2 -c "cd /home/frappe/frappe-bench && env/bin/pip install -e apps/marketplace"
docker commit --change 'ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]' --change 'CMD ["start.sh"]'   --change 'USER frappe' --change 'WORKDIR /home/frappe/frappe-bench' mp-build frappe:16-accounting-890d5fc-r3
docker rm mp-build

# 3. Compose: next to each of the 7 accounting bind mounts add
#      - type: bind
#        source: /home/ubuntu/edariba-apps/marketplace
#        target: /home/frappe/frappe-bench/apps/marketplace
#    and change every image ...-r2 to ...-r3; then
docker compose --project-name edariba -f ~/gitops/frappe-v16.yml config -q
docker compose --project-name edariba -f ~/gitops/frappe-v16.yml up -d

# 4. Install on the site (syncs DocTypes and the Moderator role fixture)
docker exec edariba-backend-1 bench --site server.edariba.com install-app marketplace

# 5. Config (secrets from the team password store, never from git)
docker exec edariba-backend-1 bench --site server.edariba.com set-config qdrant_url "http://84.235.250.108:9080"
docker exec edariba-backend-1 bench --site server.edariba.com set-config embedding_api_url "http://44.194.201.67:3778/embed"
docker exec edariba-backend-1 bench --site server.edariba.com set-config embedding_api_key "<key>"   # NOT set yet
# marketplace_app_url defaults to https://app.edariba.com

# 6. Qdrant collections (done)
for c in marketplace_accountants marketplace_services marketplace_projects; do
  curl -X PUT "http://84.235.250.108:9080/collections/$c" -H 'Content-Type: application/json'     -d '{"vectors": {"size": 1024, "distance": "Cosine"}}'
done
```

Then give the sales / customer-support team the **Marketplace Moderator** role in Desk.

**Check after deploy**
- `GET https://server.edariba.com/api/method/marketplace.api.public.metadata.get_metadata` → `success: true`.
- As a guest, `POST /api/resource/Marketplace Inquiry` → 403.
- Logged in: `workspace.list_requests` → empty list, not an error.

**Later updates**: `cd ~/edariba-apps/marketplace && git pull`, then
`docker exec edariba-backend-1 bench --site server.edariba.com migrate` and
`docker restart edariba-backend-1 edariba-frontend-1 edariba-websocket-1 edariba-scheduler-1 edariba-queue-short-1 edariba-queue-long-1`.
No image rebuild is needed for code changes (the install is editable); only
for a change to `pyproject.toml` dependencies.

**Rollback** (order matters: the site breaks if the code disappears while the
app is still installed): first
`bench --site server.edariba.com uninstall-app marketplace --yes`
(drops the marketplace tables), then restore
`~/gitops/frappe-v16.yml.bak-20261020-1724-pre-marketplace` (r2, no mount)
and `up -d`. The database backup taken just before install is
`sites/server.edariba.com/backups/20261020_202444-server_edariba_com-database.sql.gz`.

**WordPress**: the gateway URL is now
`/api/method/marketplace.api.gateway.request`; update
`class-frappe-client.php` and set `EDARIBA_FRAPPE_API_URL` in wp-config.php.
