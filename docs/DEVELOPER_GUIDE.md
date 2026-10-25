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
- **`auto_intent=1`** is the "AI assistant" box: send the user's sentence as `query` and the backend picks the entity type (and category, when it recognises one) from keywords. `meta.intent_matched` tells you whether it understood. Use it for the home-page search box. Use plain `search` with explicit `entity_types` for a filtered results page.
- Search needs the embedding API key on the server. **Until it is set, `search.search` returns an error.** Design an error/empty state for it, and fall back to the `list_*` endpoints with `q`.

**Profile fields** (list): `name, display_name, slug, headline, profile_type, governorate, area, experience_years, avatar, bio, offers_services, accepts_projects, specialties[], is_partner`. Detail adds `case_study_title, case_study_text, qualifications[{title,issuer,year}], published_services[]`.

**Service fields**: `name, title, slug, provider (profile slug), category, price, currency, price_unit (Total|Monthly|Per Session), description, badges[], features[]`.

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

The marketplace plugin and templates are **not on `main` yet**. They are on branch **`feat/marketplace-stitch-ui`** of the `edariba-theme` repo:

```
plugins/edariba-marketplace/
  edariba-marketplace.php
  includes/class-frappe-client.php        HTTP client → gateway (the only place that talks to Frappe)
  includes/class-frappe-adapter.php       Frappe fields → the array shape templates use
  includes/class-marketplace-repository.php  templates read only through this
  includes/class-dummy-data-provider.php  demo data
  includes/class-routes.php               /marketplace/* rewrite rules
  includes/class-search-service.php       PHP search over fetched rows
  includes/class-chat-router.php          PHP keyword router (duplicate of the backend's)
  includes/class-seo-integration.php      noindex while demo mode is on
  includes/helpers.php                    edariba_mp_url(), edariba_mp_repo(), formatting
themes/edariba-theme/marketplace/*.php    page templates + partials
```

Routes: `/marketplace/`, `/marketplace/accountants[/slug]`, `/marketplace/services[/slug]`, `/marketplace/projects[/slug]`, `/marketplace/search`.

### 5.2 Configure

In `wp-config.php` (never commit it):

```php
define( 'EDARIBA_FRAPPE_API_URL', 'https://server.edariba.com' );
```

Without it the plugin runs entirely on dummy data.

### 5.3 Required fixes before going live

These are bugs in the plugin as it stands. Until 1 and 2 are fixed, **WordPress shows dummy data even when configured**.

1. **Gateway URL changed.** `class-frappe-client.php` posts to `api/method/edariba_marketplace.api.marketplace.gateway.request`. It is now:

   ```php
   'api/method/marketplace.api.gateway.request'
   ```

2. **Unwrap Frappe's `message`.** The client checks `$decoded['success']`, but Frappe returns `{"message": {"success": true, …}}`, so the check always fails and the repository falls back to dummy data. Read the envelope from `message`:

   ```php
   $decoded  = json_decode( wp_remote_retrieve_body( $response ), true );
   $envelope = is_array( $decoded ) ? ( $decoded['message'] ?? null ) : null;
   if ( ! is_array( $envelope ) || empty( $envelope['success'] ) ) {
       return null;
   }
   $data = array(
       'data'       => $envelope['data'] ?? null,
       'pagination' => $envelope['pagination'] ?? null,
       'meta'       => $envelope['meta'] ?? array(),
   );
   ```

3. **Never show dummy data in production.** `Marketplace_Repository` falls back to `Dummy_Data_Provider` on *any* failure, including a real 404. That can show invented accountants under real URLs. When demo mode is off:
   - a missing record → the WordPress 404 template;
   - Frappe unreachable → an error/empty state;
   - never dummy data.

   Keep the fallback only when `edariba_mp_is_demo_mode()` is true, and turn demo mode off in production so `Seo_Integration` stops forcing `noindex`.

4. **Use server-side search and pagination.** The repository fetches `page_size => 50` and `Search_Service` filters in PHP, so record 51+ is invisible. Pass `q`, filters, `page` and `page_size` through to the list actions and render the backend's `pagination`.

5. **Wire the AI box to the backend.** On the home page, send the visitor's sentence to `search/query` with `auto_intent => 1` instead of `class-chat-router.php`, and retire the PHP router (the backend's `intent_router.py` is the same keyword list). Keep a fallback to `list` with `q` while search returns errors (embedding key not set yet).

6. **Map the new fields.** `Frappe_Adapter::accountant()` should also pass `is_partner` (show the "شريك eDariba" badge), `offers_services` and `accepts_projects`.

7. **Fix `/join`.** `marketplace-home.php` links to `https://app.edariba.com/join`, which doesn't exist. Use `/signup`.

### 5.4 Calls to action → the app

WordPress never submits forms. Replace the demo form and demo buttons (`data-edariba-demo-form`, `data-edariba-demo-action`) with plain links into the app, carrying **public slugs only**:

| Template | Button | Link |
|---|---|---|
| `accountant-profile.php` | "استفسار مباشر وسري" form → button **"أرسل طلبًا"** | `https://app.edariba.com/marketplace/request/new?profile={slug}` |
| `service-detail.php` | **"اطلب الخدمة الآن"** | `https://app.edariba.com/marketplace/request/new?profile={provider_slug}&service={slug}` |
| `project-detail.php` | **"تقديم عرض"** | Not available yet (proposals have no API). Hide the button or link to the app's project page once Phase B ships. |

Suggested helper next to `edariba_mp_url()`:

```php
function edariba_mp_app_url( string $route, array $args = array() ): string {
	$routes = array( 'request' => '/marketplace/request/new' );   // allowlist
	if ( ! isset( $routes[ $route ] ) ) {
		return 'https://app.edariba.com/';
	}
	$args = array_map( 'sanitize_title', array_filter( $args ) ); // slugs only
	return add_query_arg( $args, 'https://app.edariba.com' . $routes[ $route ] );
}
```

Hide the button when `offers_services` is false (the backend would reject the request anyway).

### 5.5 Caching

`Frappe_Client` caches each gateway response in a transient for 5 minutes, which matches the backend's own cache. After a moderator publishes a profile, it can take up to 5 minutes (plus WP Rocket's page cache) to appear. Don't cache error responses.

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
| AI search box (WP) | gateway `search/query {query, auto_intent: 1}` |
| Filters (categories, governorates) | `metadata.get_metadata` / gateway `metadata/get` |
| Send a request (app) | `workspace.submit_request` |
| My requests (app) | `workspace.list_requests {box}` |
| Request page / email link (app) | `workspace.get_request {name}` |
| Reply (app) | `workspace.respond_request` |
| Accept / decline / cancel / close (app) | `workspace.set_request_status` |

Questions about backend behaviour: read the code in `marketplace/api/` first. Each module's docstring states its rules.
