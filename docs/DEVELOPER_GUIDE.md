# Marketplace Developer Guide

For developers building on the `marketplace` Frappe app:

- **App developers** working in `pre-edariba` (app.edariba.com, Vue 3), who build the logged-in screens.
- **WordPress developers** working in `edariba-theme` (edariba.com), who build the public SEO pages.

The backend is live on `server.edariba.com` (installed 2026-10-20). This guide covers what you can call, what comes back, the rules the backend enforces, and the work left on each side. For how the backend is built and deployed, see the repo [README](../README.md). Field-by-field DocType reference: [DOCTYPES.md](DOCTYPES.md). Ready-made requests: [`postman/`](../postman/eDariba-Marketplace.postman_collection.json).

---

## 1. The big picture

```
 Visitor (anonymous)                       Logged-in user
        │                                         │
        ▼                                         ▼
 edariba.com/marketplace/*            app.edariba.com/marketplace/*
 WordPress plugin + theme             pre-edariba (Vue SPA)
 server-side PHP, cached 5 min        browser, session cookie
        │  POST gateway.request                   │  /logic/api/method/marketplace.api.workspace.*
        │  (Guest, read-only)                     │  (same-origin proxy → server.edariba.com)
        ▼                                         ▼
 ┌────────────────────────── server.edariba.com (Frappe 16) ──────────────────────────┐
 │  accounting app (users, tenants, ETA)      marketplace app (this repo)            │
 │                                             api/public/*   api/gateway.py  Guest  │
 │                                             api/workspace.py               Login  │
 └─────────────────────────────────────────────────────┬──────────────────────────────┘
                                                       │ semantic search
                                                       ▼
                                        Qdrant (marketplace_* collections)
                                        + embedding API (BGE-M3)
```

The split is simple and on purpose:

| | WordPress (edariba.com) | App (app.edariba.com) |
|---|---|---|
| Who | Anyone, no login | Logged-in users |
| Does | Browse, search, view details (SEO) | Send requests, track them, reply as an accountant |
| Writes data? | **Never** | Yes, only through `marketplace.api.workspace.*` |
| Auth | None (Guest) | Frappe session cookie (`sid`) via `/logic` |

WordPress never logs anyone in. Every "do something" button on WordPress is a plain link into the app, which handles login and then the action (section 5.4).

---

## 2. Concepts you need

### One user, many roles

There are no "provider" or "client" accounts. What a user can do in the marketplace depends on the records they have:

| The user… | Because… |
|---|---|
| can send a request to an accountant | they are logged in (anyone) |
| is an accountant (listed, receives requests) | they own a **Marketplace Profile** with `offers_services = 1`, Verified and Published |
| is a freelancer (can send proposals) | their profile has `accepts_projects = 1` |
| has the **partner badge** (`is_partner: true`) | their own tenant has an active Partner (reseller) plan in accounting |

One person can be all of these at once, and also an Owner or Member in accounting workspaces. Those workspace roles live in `accounting` and the marketplace doesn't read them.

Each user has **at most one profile**. Profiles are created and verified by staff with the **Marketplace Moderator** role in Desk (`server.edariba.com/app/marketplace-profile`). Self-service profile editing is not built yet (section 6).

### Entities

| DocType | What it is | Public? |
|---|---|---|
| Marketplace Profile | An accountant / firm page | Yes, when Published |
| Marketplace Service | A priced service offered by a profile | Yes, when Published |
| Marketplace Project | A job posted by a client | Yes, when Published |
| Marketplace Inquiry | A **request** from a logged-in client to one accountant | Never. Requester and recipient only. |
| Marketplace Proposal | A freelancer's bid on a project | Never (no API yet, Desk only) |
| Marketplace Category | Shared taxonomy | Yes |

The code calls a request an "Inquiry" (DocType) and the API calls it a "request". They are the same thing.

### Request lifecycle

```
            respond (provider)            accept (provider)          close (either)
   New ───────────────────────► Responded ─────────────────► Accepted ───────────► Closed
    │  \                            │  \
    │   └── accept/decline ───┐     │   └── decline (provider) ──► Declined
    │       (provider)        │     │
    └── cancel (requester) ───┴─────┴── cancel (requester) ──────► Cancelled
```

- The provider can **respond** (write or edit the reply) while the request is `New` or `Responded`. Responding sets `Responded`.
- `Declined`, `Closed` and `Cancelled` are final.
- You never need to hard-code these rules. `get_request` returns `next_statuses` and `can_respond` for the current user, so render buttons from those.

### Emails (automatic, nothing to call)

| When | Who gets it |
|---|---|
| A request is submitted | The accountant |
| The accountant replies, edits the reply, accepts, declines or closes | The client |
| The client cancels or closes | The accountant |

Nobody is emailed about their own action. Emails contain only a name and a link to `https://app.edariba.com/marketplace/requests/<id>`. **The app must serve that route** (section 4.3).

---

## 3. API reference

### 3.1 Calling convention

Every endpoint is a Frappe whitelisted method:

```
POST https://server.edariba.com/api/method/<dotted.path>
Content-Type: application/json
```

**Frappe wraps every return value in `message`.** All marketplace endpoints return this envelope inside it:

```json
{
  "message": {
    "success": true,
    "data": { },
    "pagination": { "page": 1, "page_size": 20, "total": 42, "has_more": true },
    "meta": { }
  }
}
```

`pagination` is only present on list endpoints. Nothing unwraps `message` for you: `frappe-js-sdk`'s `call.get/post` return the raw body, so in the app read `result.message` (as `ResellerDashboard.vue` does), and in PHP read `$body['message']`.

### 3.2 Errors

Errors are standard Frappe errors, not the envelope:

| HTTP | Meaning | Typical cause |
|---|---|---|
| 403 | Not allowed | Guest calling a workspace method; acting on someone else's request; forbidden status change |
| 404 | Not found | Unknown slug; request id that isn't yours (deliberately the same as missing) |
| 417 | Validation error | Missing/unknown params, empty details, accountant not available, duplicate open request |
| 429 | Rate limited | More than 10 requests per hour by the same user |
| 5xx | Server/search outage | Qdrant or embedding API down (search only) |

The user-facing message is in `_server_messages`, a JSON string containing a list of JSON strings:

```js
const msgs = JSON.parse(err._server_messages || '[]').map((m) => JSON.parse(m).message)
```

In the app, `ens.call` already routes errors to the toast (`src/services/error.js`), so you normally don't parse this yourself.

### 3.3 Public endpoints (Guest, read-only)

Base path `marketplace.api.public`. Everything below returns **published records only**.

| Method | Params | `data` |
|---|---|---|
| `accountants.list_accountants` | `q, specialty, governorate, page=1, page_size=20 (max 50), sort_by=experience_years\|display_name, sort_order=asc\|desc` | list of profiles |
| `accountants.get_accountant` | `slug` | profile detail + `published_services` |
| `services.list_services` | `q, category, provider, min_price, max_price, page, page_size, sort_by=price\|title, sort_order` | list of services |
| `services.get_service` | `slug` | service + `provider_name`, `provider_slug` |
| `projects.list_projects` | `q, category, skills, budget_min, budget_max, page, page_size, sort_by=budget_min\|deadline, sort_order` | list of projects |
| `projects.get_project` | `slug` | project detail |
| `metadata.get_metadata` | none | `{categories:[{title,slug}], governorates, client_types, price_units}` (cached 5 min) |
| `search.search` | `query` (required), `entity_types: ["accountant","service","project"]`, `filters: {location, specialty}`, `page, page_size (max 25)`, `auto_intent` | ranked mixed results, each with `entity_type` and `score` |

Notes:

- `q` is a plain substring match on name/headline (accountants) or title (services, projects). `%` and `_` are literal.
- Search is by meaning: send the user's sentence as `query`. Without `entity_types` it searches all three collections and ranks the merged results by score; pass `entity_types` to search one type (WordPress does this per tab). `auto_intent=1` (keyword intent guessing) is not used by WordPress.
- Search needs the embedding API key on the server. **Until it is set, `search.search` returns an error.** Design an error/empty state for it, and fall back to the `list_*` endpoints with `q`.

**Profile fields** (list): `name, display_name, slug, headline, profile_type, governorate, area, experience_years, avatar, bio, offers_services, accepts_projects, specialties[], is_partner`. Detail adds `case_study_title, case_study_text, qualifications[{title,issuer,year}], published_services[]`.

**Service fields**: `name, title, slug, provider (profile slug), category, price, currency, price_unit (Total|Monthly|Per Session), thumbnail, description, badges[], features[]`.

**Project fields**: `name, title, slug, category, client_display_name, client_type, budget_min, budget_max, currency, deadline, escrow, published_at, description, required_skills[]`.

`name` equals `slug` today (records are named by slug), but **always link by `slug`**.

Personal data is never public: the owner's login (`Profile.user`, `Project.client`) and `verification_status` are hidden from Guests even through `/api/resource`.

### 3.4 Gateway (WordPress only)

```
POST /api/method/marketplace.api.gateway.request
{"resource": "accountant", "action": "list", "params": { ...same params as the public method... }}
```

| resource / action | Same as |
|---|---|
| `accountant/list`, `accountant/get` | `accountants.list_accountants`, `get_accountant` |
| `service/list`, `service/get` | `services.list_services`, `get_service` |
| `project/list`, `project/get` | `projects.list_projects`, `get_project` |
| `metadata/get` | `metadata.get_metadata` |
| `search/query` | `search.search` (incl. `auto_intent`) |

An unknown or missing param returns **417** with a message naming the bad keys and listing the allowed ones. The gateway is read-only. There is no write action.

### 3.5 Workspace endpoints (login required, app only)

Base path `marketplace.api.workspace`. Guests get 403. The backend takes the user from the session and **ignores any user/requester you send**.

#### `submit_request` (POST)

| Param | Required | Notes |
|---|---|---|
| `recipient` | yes | Profile **slug** |
| `details` | yes | Free text, non-empty |
| `inquiry_type` | no | `tax_audit`, `einvoice`, `annual_return`, `consultation` |
| `related_service` | no | Service slug; must belong to `recipient` and be published |
| `phone` | no | Defaults to the user's mobile number |

The backend rejects the request (417) when:
- the accountant isn't Published, isn't Verified, or doesn't offer services;
- the user is sending to their own profile;
- the service isn't the accountant's;
- the user already has an open request (New, Responded or Accepted) with this accountant.

It also allows at most **10 requests per hour per user** (429). Name, email and phone come from the user's account. On success it returns the request in the `get_request` shape below.

#### `list_requests` (GET or POST)

| Param | Default | Notes |
|---|---|---|
| `box` | `sent` | `sent` = requests I sent; `received` = requests to my profile (empty if I have none) |
| `status` | none | One of the six statuses |
| `page`, `page_size` | 1, 20 | `page_size` max 50 |

Rows: `name, recipient, recipient_display_name, related_service, inquiry_type, status, created_at, responded_at` (+ `requester_name` in `received`). Newest first.

#### `get_request` (GET or POST): `name`

```json
{
  "name": "a1b2c3d4e5",
  "role": "requester",                    // or "provider": which side you are
  "status": "Responded",
  "inquiry_type": "consultation",
  "details": "…",
  "created_at": "2026-10-20 18:02:11",
  "response": "…", "responded_at": "…",
  "recipient": { "name": "hesham-elqadi", "display_name": "…", "slug": "hesham-elqadi" },
  "related_service": { "name": "…", "title": "…", "slug": "…" },   // or null
  "next_statuses": ["Cancelled"],         // buttons to show
  "can_respond": false,                   // show the reply box?
  "requester": { "name": "…", "email": "…", "phone": "…" }          // provider only
}
```

A request that isn't yours returns 404, exactly like a missing one.

#### `respond_request` (POST): `name, message`

Provider only, while `can_respond` is true. Sets `Responded` (calling it again edits the reply). Returns the updated request.

#### `set_request_status` (POST): `name, status`

`status` must be in that request's `next_statuses`, otherwise 403. Returns the updated request.

---

## 4. App developers (pre-edariba)

Read `pre-edariba/CLAUDE.md` first. The rules below are the marketplace-specific parts.

### 4.1 Local setup

```bash
cd pre-edariba
npm install
npm run dev
```

> **Warning:** the Vite dev server proxies `/logic` to **production** (`vite.config.js`, `'/logic'` → `https://server.edariba.com`). Everything you do locally hits real data and sends real emails. Use test accounts, not real customers.

To exercise both sides of a request you need **two accounts**: a client, and an accountant whose profile a moderator has created, Verified and Published in Desk.

### 4.2 Calling the backend

Follow the existing pattern: add wrappers in `src/services/logic.js` and call them from pages through `ens.call`. Look at `resellerDashboard` / `ResellerDashboard.vue` as the reference.

```js
// src/services/logic.js — next to the other feature blocks
////////////////////// Marketplace
const MP = 'marketplace.api.workspace'

async function marketplaceSubmitRequest(data) {
  await ensureFrappe()
  return await call.post(`${MP}.submit_request`, data)
}
async function marketplaceListRequests(params) {
  await ensureFrappe()
  return await call.get(`${MP}.list_requests`, params)
}
async function marketplaceGetRequest(name) {
  await ensureFrappe()
  return await call.get(`${MP}.get_request`, { name })
}
async function marketplaceRespond(name, message) {
  await ensureFrappe()
  return await call.post(`${MP}.respond_request`, { name, message })
}
async function marketplaceSetStatus(name, status) {
  await ensureFrappe()
  return await call.post(`${MP}.set_request_status`, { name, status })
}
// …and add them to the exported `ens` object at the bottom of the file.
```

```js
// in a page. `params` is an array: ens.call spreads it into the wrapper's arguments
const res = await ens.call({ funcData: 'logic.marketplaceGetRequest', params: ['a1b2c3d4e5'], freeze: false })
const { data: request } = res.message          // { success, data, pagination?, meta }

const list = await ens.call({
  funcData: 'logic.marketplaceListRequests',
  params: [{ box: 'received', page: 1 }],
  freeze: false,
})
const { data: rows, pagination } = list.message
```

Public data (profile/service details for the request form) comes from the public endpoints. Wrap them the same way (`marketplace.api.public.accountants.get_accountant`). They work with or without a session.

**No IndexedDB here.** The 3-layer IndexedDB rule in `CLAUDE.md` is for company-scoped ETA documents. Marketplace requests are small, user-scoped and server-paginated: use a small Pinia store (or page state) and fetch per page. Note this in your PR so the reviewer doesn't flag it.

### 4.3 Screens to build

| Route | Screen | Calls |
|---|---|---|
| `/marketplace/request/new?profile=<slug>&service=<slug>` | Request form. Deep-link target from WordPress; not in the sidebar. | `get_accountant` (and `get_service`) to show who you're writing to; `submit_request` |
| `/marketplace/requests` | One page, two tabs: **المُرسلة** (`box=sent`) and **الواردة** (`box=received`, only if the user has a profile) | `list_requests` |
| `/marketplace/requests/:id` | Detail: status, details, reply, action buttons from `next_statuses`, reply box when `can_respond`. **This is the link in every email.** | `get_request`, `respond_request`, `set_request_status` |

Sidebar (`src/layouts/sidebar.vue`): add a group **السوق** with `/marketplace/requests`. Phase B adds provider pages (`/marketplace/profile`, `/marketplace/services`) behind a new `providerOnly` flag, using the same mechanism as `resellerOnly`.

States every screen needs:

- **Accountant unavailable** (417 on submit, or the profile fetch fails): show "هذا المحاسب غير متاح حاليًا" instead of the form.
- **Duplicate** (417 "already have an open request"): link to the existing request in "المُرسلة".
- **Rate limited** (429): ask them to try later.
- **Empty lists**: use `EmptyPage.vue`.
- **Not your request** (404 on `/marketplace/requests/:id`): a normal not-found page.

Copy is Arabic-first (RTL). Use `notify.*` for feedback, never `alert`.

### 4.4 Login and return-to-action (required change)

A logged-out visitor arrives from WordPress on `/marketplace/request/new?profile=…`. Today:

- The global guard (`src/router/index.js`, the `beforeEach` that checks `isUserAuthenticatedFromStorage()`) returns `{ name: 'signup' }` and **drops the target URL**.
- `login.vue` already honours `?redirect=` for in-app paths only (`startsWith('/') && !startsWith('//')`).
- Signup is email-verify → set password → login, so the target must survive an email round trip.

What to do:

1. In the guard, return `{ name: 'signup', query: { redirect: to.fullPath } }` and save `to.fullPath` to `localStorage` as `pendingIntent` (only in-app paths; reuse `login.vue`'s check).
2. Carry `redirect` through signup ↔ login links and the set-password step.
3. After login, if `pendingIntent` exists, consume and clear it, then navigate there.

**Onboarding is not skipped**: every user goes through ETA onboarding first (decision J2). After onboarding, the user should still land on `pendingIntent`.

### 4.5 Tests

- Vitest: the redirect guard and `pendingIntent` (accepts `/marketplace/...`, rejects `//evil.com` and `https://…`).
- Playwright: logged-out deep link → login → form → submit → appears in "المُرسلة". Then as the accountant account: appears in "الواردة" → reply → client sees the reply.

---

## 5. WordPress developers (edariba-theme)

### 5.1 Where the code is

The marketplace plugin and templates are **not on `main` yet** (`main` reverted the merge). They are on branch **`feat/marketplace-stitch-ui`** of the `edariba-theme` repo:

```
plugins/edariba-marketplace/
  edariba-marketplace.php
  includes/class-frappe-client.php        HTTP client → gateway (the only place that talks to Frappe)
  includes/class-frappe-adapter.php       Frappe fields → the array shape templates use
  includes/class-marketplace-repository.php  templates read only through this
  includes/class-search-service.php       list/search params → backend; PHP matching only in demo mode
  includes/class-dummy-data-provider.php  demo data (demo mode only)
  includes/class-routes.php               /marketplace/* rewrite rules
  includes/class-seo-integration.php      noindex in demo mode and on search pages, canonical URLs
  includes/class-sitemap.php              /marketplace-sitemap.xml, added to Rank Math's index and robots.txt
  includes/helpers.php                    edariba_mp_url(), edariba_mp_app_url(), edariba_mp_avatar(), formatting
themes/edariba-theme/marketplace/*.php    page templates + partials
```

Routes: `/marketplace/`, `/marketplace/accountants[/slug]`, `/marketplace/services[/slug]`, `/marketplace/projects[/slug]`, `/marketplace/search`, plus `/marketplace-sitemap.xml`.

### 5.2 Configure

The plugin calls the gateway through the web app's `/logic` proxy by default:

```php
define( 'EDARIBA_FRAPPE_API_URL', 'https://app.edariba.com/logic' ); // default, set in the plugin
```

Define it in `wp-config.php` only to point elsewhere, or as `''` to run on demo data.

**Demo mode** is on only when no API URL is set. With the backend configured, demo data is never shown: a missing record is a 404, an outage is a 503 page / empty list. To keep demo data (and `noindex`) on purpose, add `add_filter( 'edariba_mp_demo_mode', '__return_true' );`.

### 5.3 How the plugin uses the backend

- **Gateway:** `api/method/marketplace.api.gateway.request`; the envelope is read from Frappe's `message`.
- **Lists:** query, filters, sort and page go to the `list` actions; pagination comes from the backend.
- **Search page:** no intent guessing. The tab comes from `?tab` (default accountants); inside it, the query is searched by meaning (`search/query` with `entity_types: [<tab>]`, `filters.location` = governorate). While search fails (e.g. embedding key not set) it falls back to the `list` action with `q`, and stops calling search for 60 s after a failure. Counts are hidden for meaning results.
- **Profiles:** `is_partner` shows the "شريك eDariba" badge; `offers_services = false` hides the request button. Missing avatars/thumbnails render an initial badge/icon panel.
- **Categories and governorates** come from `metadata/get`.

Known backend limits that show in WordPress:

- `search.search` returns `total` from an over-fetch (`min(page × page_size × 2, 100)` per collection), so the page count of meaning results is approximate.
- Meaning search only filters by `location` (and `specialty`, matched against `specialization_ids`); category, price and budget filters apply to keyword lists only.

### 5.4 Calls to action → the app

WordPress never submits forms. Buttons are plain links into the app carrying **public slugs only** (`edariba_mp_app_url()`, allowlisted routes):

| Template | Button | Link |
|---|---|---|
| `accountant-profile.php` | **"أرسل طلبًا"** | `https://app.edariba.com/marketplace/request/new?profile={slug}` |
| `service-detail.php` | **"اطلب الخدمة الآن"** | `https://app.edariba.com/marketplace/request/new?profile={provider_slug}&service={slug}` |
| `project-detail.php`, `card-project.php` | none | Proposals have no API yet; a note points to the app. |

### 5.5 Caching

`Frappe_Client` caches each successful gateway response in a transient for 5 minutes, which matches the backend's own cache; errors are never cached. The sitemap is cached for 1 hour. After a moderator publishes a profile, it can take up to 5 minutes (plus WP Rocket's page cache) to appear.

---

## 6. Not built yet

| Gap | Impact | Who |
|---|---|---|
| Profile and service self-service (`get/save_my_profile`, `list/save_my_service`) | Moderators create profiles in Desk for now | Backend + app (Phase B) |
| Project posting and proposals API | Project pages are read-only; "تقديم عرض" has nowhere to go | Backend + app (Phase B) |
| Embedding API key on the server | `search.search` errors until set | Ops |
| Partners ranked higher | Badge is shown, ordering unchanged | Backend |
| Marketplace items in the app's notification bell | Users rely on email + the requests page | App (Phase B) |

If you need an endpoint that isn't here, ask for it in the marketplace repo rather than calling `/api/resource/Marketplace …` directly. Logged-in users have no permissions there by design, so it will return 403.

---

## 7. Quick reference

| Need | Call |
|---|---|
| Directory page (WP) | gateway `accountant/list` |
| Accountant page (WP) | gateway `accountant/get {slug}` |
| AI search box (WP) | gateway `search/query {query, entity_types: [<tab>]}`, fallback `<tab>/list {q}` |
| Filters (categories, governorates) | `metadata.get_metadata` / gateway `metadata/get` |
| Send a request (app) | `workspace.submit_request` |
| My requests (app) | `workspace.list_requests {box}` |
| Request page / email link (app) | `workspace.get_request {name}` |
| Reply (app) | `workspace.respond_request` |
| Accept / decline / cancel / close (app) | `workspace.set_request_status` |

Questions about backend behaviour: read the code in `marketplace/api/` first. Each module's docstring states its rules.
