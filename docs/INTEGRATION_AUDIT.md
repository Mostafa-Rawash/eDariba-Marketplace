# eDariba Marketplace — Integration Audit & UI Placement Recommendation

> **Status update (2026-10-20).** This report is a point-in-time audit. Module paths below were updated to the new layout (`api/public/`, `api/gateway.py`, flat `services/`); references to `eDariba-Marketplace/edariba_marketplace/` mean the repo root now. **The app was renamed `edariba_marketplace` → `marketplace` on 2026-10-20**: read `edariba_marketplace` below as `marketplace` (except the legacy Qdrant collection of that name). Decisions taken since:
> - **J1** yes: install on server.edariba.com beside `accounting`. No `accounting` code changes.
> - **J2** no exemption: everyone goes through ETA onboarding.
> - **J3** login required. Guest inquiry endpoint and Guest create DocPerm removed (fixes **S1**).
> - **J4 = C**: anyone can apply, a moderator verifies, an active Partner plan shows an `is_partner` badge.
> - **J5**: a request belongs to the User only; no company link in v1.
> - **J6**: implemented as `New → Responded → Accepted → Closed`, Declined by the provider, Cancelled by the requester (`services/request_rules.py`).
> - Roles: no `Marketplace Provider` / `Marketplace Client` roles. One profile per user with `offers_services` / `accepts_projects` switches; only `Marketplace Moderator` is added (fixture).
> - `chat.discover` merged into `search.search(auto_intent=1)`.
> - Qdrant collections renamed to `marketplace_accountants` / `marketplace_services` / `marketplace_projects` (fixes **S6**: no more sharing `accountants` with unrelated records).
> - Done in the backend: A1 (packaging), A2, A3 (as above), A4 (`api/workspace.py`), A5 (emails), A9. See `README.md` for what remains and the deploy steps.

## Context

The Marketplace was built in three separate places: a WordPress plugin and theme templates, a new Frappe app (`edariba_marketplace`), and a Qdrant/embedding layer. None of it has been tested end to end, and none of it is connected to the authenticated product (`pre-edariba` at app.edariba.com, backed by Frappe at server.edariba.com). This report covers what exists, where each Marketplace feature should live, and the smallest secure integration that connects the full journey: discovery → login → request → notification → response.

**Method.** Everything here comes from reading the code. Nothing was run (no bench, no tests, no network). Claims are tagged **[V]** (verified in code) or **[U]** (unverified or not in any repo).

---

## A. Current Architecture

| Layer | Actual system | Evidence |
|---|---|---|
| Public site | WordPress at **edariba.com**. Marketplace lives under `/marketplace/*` (rewrite rules, no CPTs) | `edariba-theme/plugins/edariba-marketplace/includes/class-routes.php` [V] |
| Authenticated app | **pre-edariba**: Vue 3 Options API SPA at **app.edariba.com** (Vercel) | `pre-edariba/vercel.json`, `INDEX.md` [V] |
| Core backend / identity | Frappe site **server.edariba.com**, reached first-party through the SPA's `/logic/*` rewrite (`vercel.json`, `vite.config.js:302`). App `accounting` | [V] |
| Marketplace backend | Separate Frappe app `eDariba-Marketplace/edariba_marketplace` (1 commit, `5c87f7c`). **Which site it is installed on is unknown.** The README says the live site could never be inspected. Postman `base_url` = `http://localhost:8000` | `eDariba-Marketplace/edariba_marketplace/README.md` [U for deployment] |
| Search | Qdrant (unauthenticated REST) + BGE-M3 embedding API (plain HTTP to a raw IP). One collection per entity: `accountants` / `services` / `projects` | `services/config.py`, `qdrant_client.py`, `embedding_client.py` [V code; U runtime] |
| Hostname in brief | `abet.erp.com` **does not appear in any repo**. The real hosts are edariba.com / app.edariba.com / server.edariba.com | grep [V] |
| WP → Frappe link | One gateway call `POST {EDARIBA_FRAPPE_API_URL}/api/method/edariba_marketplace.api.gateway.request`, sent as Guest, cached 5 min in transients. **Disabled unless `EDARIBA_FRAPPE_API_URL` is defined in wp-config.php** (wp-config is not in the repo) | `class-frappe-client.php` [V code; U config] |

**Stacks.** pre-edariba: Vue 3, Vite, Pinia, PrimeVue, Tailwind/DaisyUI, frappe-js-sdk. Backend: Frappe (version not pinned in the repo [U]). WP plugin: PHP 8, WP 6+.

---

## B. Existing Functionality Inventory

### B1. `edariba_marketplace` Frappe app
- **DocTypes** (`edariba_marketplace/marketplace/doctype/`):
  - **Marketplace Profile**: named by slug. Fields: `user` (User, reqd), `profile_type`, `display_name`, `headline`, `governorate` (5 options), `experience_years`, `bio`, `specialties` (Tag table), `qualifications`, `case_study_*`, `verification_status` (Pending/Verified/Rejected, RO), `publication_status` (Draft/Published/Unpublished).
  - **Marketplace Service**: `provider` → Profile, `category`, `price`, `price_unit`, `thumbnail` (reqd), `badges`, `features`, `publication_status`.
  - **Marketplace Project**: `client` (User), `client_display_name`, `client_type`, `budget_min/max`, `deadline`, `escrow`, `publication_status` (Draft/Published/Closed/Archived).
  - **Marketplace Proposal**: `project`, `freelancer` → Profile, `submitted_by` (User, RO), `proposed_amount`, `estimated_days`, `cover_letter`, `status` (Submitted/Shortlisted/Accepted/Rejected/Withdrawn).
  - **Marketplace Inquiry**: `recipient` → Profile, `related_service`, `requester_name/email/phone`, `inquiry_type`, `details`, `status` (New/Contacted/Closed). **There is no link to a requester User.**
  - **Marketplace Category**, plus child tables Tag and Qualification.
- **Controllers.**
  - Profile: only a moderator can change verification, and only a Verified profile can publish.
  - Service and Project: ownership guards and publish-time required fields.
  - Proposal: the submitter must own the freelancer profile, cannot propose on their own project, and cannot hold two active proposals on the same project.
  - Inquiry: email validation, status forced to New.
- **Permissions** (`marketplace/permissions.py` + `hooks.py`): row-level `permission_query_conditions` and `has_permission` for all five main DocTypes. Roles referenced: `Marketplace Provider`, `Marketplace Client`, `Marketplace Moderator`, `System Manager`. **No fixture or patch creates or assigns these roles.** Frappe auto-creates missing roles on DocType sync, but no user ever receives them [V].
- **Public APIs** (all `allow_guest`, `api/public/`): `accountants.list_accountants/get_accountant`, `services.list_services/get_service`, `projects.list_projects/get_project`, `metadata.get_metadata`, `search.search` (Qdrant), `chat.discover`, `inquiry.submit_inquiry` (Guest write, rate-limited 5/h per `requester_email`), `gateway.request` (allowlisted dispatcher for all of these).
- **Indexing**: `doc_events` on Profile/Service/Project enqueue embed+upsert on the `short` queue; unpublishing deletes the point; `reconcile()` is manual and System Manager only. Search revalidates every Qdrant hit against Frappe (`search_service._PUBLIC_LOOKUP`) [V].
- **Tests**: `test_*.py` stubs per DocType (not run); `tests/test_intent_router.py` (README claims 5/5 passed; not re-run here).
- **Not present**: authenticated "my profile / my services / my requests / my proposals" endpoints, request response workflow, any email or notification, any DocType Workflow, and packaging (`pyproject.toml`/`setup.py` missing, so `bench get-app` will fail) [V].

### B2. WordPress (`edariba-theme`)
- **Plugin `plugins/edariba-marketplace/`**:
  - Routes: `/marketplace/`, `/services[/slug]`, `/accountants[/slug]`, `/projects[/slug]`, `/search`.
  - `Marketplace_Repository` tries Frappe and **silently falls back to `Dummy_Data_Provider` on any failure**.
  - `Search_Service` does PHP substring search over at most 50 fetched rows; it never calls Frappe `search` or `chat.discover`.
  - `Chat_Router` is a PHP keyword router that redirects to `/marketplace/search` (duplicated in Python `intent_router.py`).
  - `Seo_Integration` forces noindex while demo mode is on. Demo mode defaults to `true` (`edariba_mp_is_demo_mode`).
- **Templates `themes/edariba-theme/marketplace/*.php`**: real UI for home (AI search box), directories, profile, service, project, and search.
  - `accountant-profile.php:165` "استفسار مباشر وسري" form is `data-edariba-demo-form` and submits nowhere.
  - `service-detail.php:78` "اطلب الخدمة الآن" and `project-detail.php:66` "تقديم عرض" are `data-edariba-demo-action` buttons that link to `https://app.edariba.com/login`.
  - `marketplace-home.php:370` links to `https://app.edariba.com/join`. **That route does not exist in the SPA router** and falls through to `notfound` [V].
- **`plugins/edariba-requests/`**: landing-page lead capture into a WP CPT. It is not a marketplace request system and should not be reused for this.
- **WP user accounts**: none for the public. Only admins exist, and `wps-hide-login` is installed. There is no SSO or OAuth plugin [V].

### B3. pre-edariba (authenticated app)
- **Auth**:
  - `UserStore.login` calls `frappe-js-sdk.loginWithUsernamePassword` against `/logic` (a Frappe `sid` cookie, first-party on app.edariba.com), then `accounting.templates.global_context.edariba_login`.
  - Google OAuth via Frappe Social Login.
  - Session check: `logic.getLoggedInUser` (403 → auto-logout).
  - `src/stores/UserStore.js:113`, `src/router/index.js:718-800` [V].
- **Return-to-action**:
  - `login.vue:245-249` already honors `?redirect=` and allows only in-app paths (starts with `/`, not `//`).
  - **The global guard sends unauthenticated users to `signup` without `redirect`** (`router/index.js:745`). Only `/payment` preserves it (`:453`).
  - Signup passes `redirect_to: ''` (`services/logic.js:705`), even though `sign_up` supports it.
  - Signup is email-verify → set password → login, so the intent must survive an email round trip [V].
- **Registration**: public, via `accounting/www/signup/index.py:sign_up`. Creates `Website User` with the Portal default role and a welcome email through the Email Queue [V].
- **Workspaces and roles**:
  - Owner/Member model (`accounting/tenant/workspace_api.py`), Member invite with expiry (`tenant/doctype/member/member.py:59`).
  - Reseller (accountant partner) plan with `/reseller` (`pages/Reseller/ResellerDashboard.vue`).
  - Sidebar flags `ownerOnly` / `resellerOnly` (`layouts/sidebar.vue:280-345`).
  - Client-side `roles` are hard-coded (`UserStore.js:_completeLogin`) [V].
- **Notifications**:
  - Header bell (`layouts/Header.vue:107-149`) shows **ETA notifications only** (`eta.getNotification`).
  - Firebase push (`services/firebase/firebaseMessaging.js`).
  - The `notify.*` toast hub.
  - **No general in-app notification center** [V].
- **Email**: `frappe.sendmail` with named templates (`member.py:303`, `template="member_invitation"`) and Email Queue + background flush (`signup/index.py:230`). Relay: HestiaCP Exim, about 200/h per account (memory note) [V code / U capacity].
- **Marketplace UI**: **none**. `docs/EXPERTS_MARKETPLACE_MVP.md` describes an "Ask an expert" in-app flow, but no code for it exists [V].
- **Reusable UI**:
  - `DataTableComp.vue`, `FiltersComponent.vue`, `EmptyPage.vue`, `components/forms/*`, and the `notify` service.
  - The page→`ens.call('logic.x')` pattern in `ResellerDashboard.vue:25`.
  - `logic.js` wrappers that call `call.get('<dotted.path>')`.

### B4. Capability classification

| Capability | Status | Evidence |
|---|---|---|
| Authenticated dashboard / app shell | **Existing & reusable** | pre-edariba `sidebar.vue`, `Header.vue`, router |
| User profile management | Existing & reusable (account), **Missing** for marketplace profile | `pages/ProfilePage/EditAccountpage.vue` |
| Accountant/professional profile mgmt | **Partially implemented** (DocType + perms only; Desk is the only UI) | `marketplace_profile/*` |
| Service management | **Partially implemented** (DocType + perms, no app UI or API) | `marketplace_service/*` |
| Project management | **Partially implemented** (same) | `marketplace_project/*` |
| Request / inquiry management | **Existing but needs modification** (Guest-only, no requester link, no response, no notification) | `marketplace_inquiry/*`, `inquiry.py` |
| Proposal submission/review | **Partially implemented** (DocType + guards, no API/UI, status not guarded) | `marketplace_proposal/*` |
| Email infrastructure | **Existing & reusable** | `frappe.sendmail` + templates (`member.py:303`) |
| Notification center | **Missing** (bell is ETA-only) | `Header.vue:107` |
| Shared auth / SSO | **Missing / not needed in the recommended design** (one identity: Frappe) | §E |
| APIs for WordPress | **Existing** (gateway), untested | `gateway.py`, `class-frappe-client.php` |
| Status/approval workflows | **Partially implemented** (Select fields + publish guards; no Frappe Workflow) | controllers |
| Qdrant semantic search | **Existing in backend, not used by WP** | `search_service.py` vs `class-search-service.php` |
| Marketplace app installed on prod site | **Cannot verify** | README |

---

## C. UI Placement Matrix

The authenticated workspace belongs in **pre-edariba (app.edariba.com)**, not Frappe Desk. Marketplace users are Website Users (Desk is not the product UI), the SPA already owns login, session, sidebar and feedback, and it reaches Frappe first-party through `/logic`.

| Feature | Role | Entry point | Reuse | Recommended route/screen | Backend endpoint | Entity | UI exists? | Change |
|---|---|---|---|---|---|---|---|---|
| Accountant directory | Visitor | WP nav / home | `accountants.php`, `card-accountant.php` | `edariba.com/marketplace/accountants/` | `accountants.list_accountants` [V] | Profile | Yes | Fix server-side `q`/pagination; turn off dummy fallback in prod |
| Accountant profile | Visitor | Directory card | `accountant-profile.php` | `/marketplace/accountants/{slug}/` | `accountants.get_accountant` [V] | Profile | Yes | Replace demo form with an **"أرسل طلبًا" CTA → app** |
| Services directory | Visitor | WP | `services.php`, `card-service.php` | `/marketplace/services/` | `services.list_services` [V] | Service | Yes | Same as directory |
| Service details | Visitor | Card | `service-detail.php` | `/marketplace/services/{slug}/` | `services.get_service` [V] | Service | Yes | CTA → app request form, pre-selecting the service |
| Projects directory | Visitor | WP | `projects.php`, `card-project.php` | `/marketplace/projects/` | `projects.list_projects` [V] | Project | Yes | Same |
| Project details | Visitor / Freelancer | Card | `project-detail.php` | `/marketplace/projects/{slug}/` | `projects.get_project` [V] | Project | Yes | CTA "تقديم عرض" → app proposal form |
| Search & Chat | Visitor | Home AI box | `marketplace-home.php` form, `marketplace-search.php` | `/marketplace/search/` | `search.search`, `chat.discover` [V, unwired] | Qdrant → Frappe | Yes (PHP-local) | Phase C: call `chat.discover` server-side and keep PHP search as fallback; retire one of the duplicate routers |
| Login / registration | All | CTA redirect | `pages/Auth/login.vue`, `signup.vue` | `app.edariba.com/login?redirect=…` | Frappe login, `sign_up` [V] | User | Yes | Preserve `redirect` in guard and signup (§E) |
| Accountant profile editing | Provider | Sidebar "السوق ← ملفي المهني" | `components/forms/*`, `EditAccountpage.vue` layout | **new** `/marketplace/profile` | **proposed** `my_profile.get/save` | Profile | No | New page; submit for verification |
| Service CRUD | Provider | Sidebar "خدماتي" | `DataTableComp`, forms | **new** `/marketplace/services` | **proposed** `my_services.list/save/unpublish` | Service | No | New page |
| Incoming requests | Provider | Sidebar "الطلبات الواردة" + email link | `DataTableComp`, `FiltersComponent`, `EmptyPage` | **new** `/marketplace/requests?box=received` | **proposed** `requests.list(box)` | Inquiry | No | New page (one page, two tabs) |
| Sent requests | Client | Same page, tab "المُرسلة" | same | `/marketplace/requests?box=sent` | **proposed** | Inquiry (+`requester`) | No | Needs `requester` field |
| Request details & response | Both | Row click / email deep link | detail-panel pattern of `InvoiceView.vue` | **new** `/marketplace/requests/:id` | **proposed** `requests.get`, `requests.respond`, `requests.set_status` | Inquiry | No | New page |
| Request form | Client | WP CTA → app | forms + `notify` | **new** `/marketplace/request/new?profile=&service=` | **proposed** `requests.submit` (auth) | Inquiry | No | New page |
| Received proposals | Client (project owner) | "مشروعاتي" → project | `DataTableComp` | `/marketplace/projects/:id/proposals` (Phase B) | **proposed** | Proposal | No | Phase B |
| Submitted proposals | Freelancer | "عروضي" | `DataTableComp` | `/marketplace/proposals` (Phase B) | **proposed** | Proposal | No | Phase B |
| Email notifications | System | Doc events | `frappe.sendmail` + template pattern (`member.py:303`) | n/a | `after_insert`/`on_update` hooks (proposed) | Inquiry/Proposal | No | Phase A |
| Notification history | Both | Header bell | `Header.vue` dropdown | Phase B: merge a marketplace source into the bell, or show unread counts in the sidebar | **proposed** `requests.unread_count` or Frappe `Notification Log` | Notification Log | Bell exists (ETA-only) | Phase B |
| Moderation | Moderator | Frappe Desk | Desk list/form views | `server.edariba.com/app/marketplace-profile` | Desk | All | Yes (Desk) | Keep in Desk, no custom UI |

**Sidebar change** (`layouts/sidebar.vue` group array near line 280): add one group "السوق" with `/marketplace/requests` (everyone) and `/marketplace/profile`, `/marketplace/services` (shown when the user has a Marketplace Profile, via a new `providerOnly` flag, same mechanism as `resellerOnly`).

---

## D. Recommended User Journeys

1. **Visitor discovery** (WP, anonymous): `/marketplace/` → search/chat → directory → detail page. Data comes from the Frappe gateway as Guest (published-only filter enforced twice: repository + permission hooks). No login needed.
2. **Request** (Client):
   1. WP profile or service page: CTA `https://app.edariba.com/marketplace/request/new?profile={slug}&service={slug}`. Only public slugs go in the URL.
   2. SPA guard: not authenticated → store the intended in-app path → `/signup?redirect=…` (or `/login?redirect=…` via "لديك حساب؟").
   3. After login, `login.vue` redirects to the validated in-app path.
   4. The form loads the profile/service through the public `get_accountant`/`get_service` (shows a "not available" state if unpublished) and pre-fills name, email, phone and company from `UserStore` and `CompanyStore`.
   5. Submit → `requests.submit` sets `requester = frappe.session.user` server-side, then checks recipient published + verified, service belongs to recipient, not self, rate limit, and duplicate-open check.
   6. `after_insert` → email to the provider (enqueued).
   7. Success toast plus a link to `/marketplace/requests/:id`.
3. **Recipient (Provider)**: email "طلب جديد" with a deep link to `app.edariba.com/marketplace/requests/{id}` (no PII beyond the requester's display name) → login if needed → detail → **respond** (short message) and/or set status → email to requester.
4. **Requester tracking**: `/marketplace/requests?box=sent` shows status and the provider response.
5. **Proposal (Phase B)**: WP project page → `app.edariba.com/marketplace/projects/{slug}/propose` → same auth path → `proposals.submit` (existing controller guards) → email to project owner → owner shortlists/accepts/rejects in `/marketplace/projects/:id/proposals` → email to freelancer. A freelance proposal stays **a separate entity** from a service inquiry (that split already exists and is correct).

---

## E. Authentication Recommendation

**Answers to the audit questions**
1. Users register in **Frappe server.edariba.com** (`sign_up`, Google social login).
2. The identity authority is **Frappe**.
3. The app authenticates with the Frappe `sid` session cookie, first-party on app.edariba.com through the `/logic` rewrite.
4. WordPress has no public user accounts (admins only).
5. There is no SSO.
6. Return-to-action exists for login (`?redirect=`, in-app only) but **is dropped by the global guard and by signup**.
7. API requests use the session cookie (SPA) or Guest (WP gateway).
8. CSRF uses Frappe's `X-Frappe-CSRF-Token` for session POSTs, handled by frappe-js-sdk. No cross-origin calls are needed because `/logic` is same-origin. CORS settings on server.edariba.com are [U] (site_config not in repo).
9. Sessions expire or are revoked through Frappe session expiry and logout; the SPA polls `getLoggedInUser` on navigation.
10. Account ownership is enforced only in Frappe (`Profile.user`, `Project.client`, `Proposal.submitted_by`, proposed `Inquiry.requester`).

**Recommended: "WP is anonymous; every protected action happens in the app" (no SSO).**
- WP never authenticates anyone. Its CTAs are plain links into allowlisted app routes carrying only public identifiers.
- This gives one identity and one sign-in UI (app.edariba.com/login) without cross-domain cookies, third-party-cookie or SameSite problems, token handoffs, or a second password store.
- Required changes, all in pre-edariba:
  1. Global guard (`router/index.js:745`): `return { name: 'signup', query: { redirect: to.fullPath } }`, and persist the path to `localStorage` as `pendingIntent` (same origin, non-sensitive) so it survives email verification and set-password.
  2. `signup.vue` / `login.vue` / set-password: carry `redirect` through ("لديك حساب؟" link, post-login), reuse `login.vue`'s existing in-app path validation, add an allowlist of `/marketplace/` prefixes, and consume and clear `pendingIntent` after login.
  3. Onboarding guard (`router/index.js:~428`) currently forces `/onboarding` for anyone who hasn't passed it. Decide whether `/marketplace/*` is exempt (a client sending one request should not have to finish ETA onboarding). **Decision J2.**
- **Rejected alternatives.**
  - Cross-origin form post from WP to Frappe: requires credentialed CORS and third-party cookies, and widens CSRF exposure.
  - Frappe OAuth provider → WP OIDC login: only worth it if WP must render personalized state ("أنت مسجّل الدخول", saved items). Revisit in Phase C if needed; Frappe ships an OAuth2 provider, so no custom auth code would be needed.
  - API keys: not user-facing and never acceptable in the browser.

---

## F. Data & API Map

**Ownership**: Frappe is authoritative for users, profiles, services, projects, inquiries, proposals and statuses. WP is presentation plus a 5-minute transient cache. Qdrant is a derived index of published Profile/Service/Project only. Requests and proposals are never indexed [V: `indexing_service._DOCTYPE_ENTITY_TYPE`].

| Workflow | DocType | Verified endpoint | Proposed endpoint (new file `api/public/workspace.py`, all `@frappe.whitelist()` non-guest) |
|---|---|---|---|
| Browse / detail | Profile/Service/Project | `gateway.request` → list/get [V] | — |
| Semantic search | Qdrant → Frappe | `search.search`, `chat.discover` [V] | — |
| Metadata | Category | `metadata.get_metadata` [V] | — |
| Submit request | Inquiry | `inquiry.submit_inquiry` (Guest) [V] | `submit_request(recipient, related_service, inquiry_type, details, phone?)` |
| List my requests | Inquiry | — | `list_requests(box='received'|'sent', status?, page)` |
| Request detail | Inquiry | — | `get_request(name)` (uses `has_inquiry_permission`) |
| Respond / status | Inquiry | — | `respond_request(name, message)`, `set_request_status(name, status)` (transition table) |
| My profile | Profile | Desk only | `get_my_profile()`, `save_my_profile(data)` (allowlisted fields; never `verification_status`) |
| My services | Service | Desk only | `list_my_services()`, `save_my_service(data)`, `set_service_publication(name, status)` |
| Proposals (B) | Proposal | — | `submit_proposal`, `list_my_proposals`, `list_project_proposals(project)`, `set_proposal_status` |
| Frontend wrappers | — | `logic.js` pattern `call.get('accounting…')` [V] | `logic.marketplace*` wrappers calling `edariba_marketplace.api.public.workspace.*` |

**Prerequisite**: `edariba_marketplace` must be installed **on the same Frappe site as `accounting` (server.edariba.com)**. Otherwise the SPA's `/logic` session cookie cannot authorize marketplace calls. **Decision J1.**

---

## G. Gap Analysis (incl. defects found in existing code)

**Blockers**
1. App is not installable: no `pyproject.toml`/`setup.py`/`patches.txt` in `eDariba-Marketplace/edariba_marketplace/`.
2. Deployment target unverified (J1). WP `EDARIBA_FRAPPE_API_URL` is unverified.
3. Inquiry has no `requester` User link, so authenticated tracking (journey C/D) is impossible.
4. No roles are ever assigned. `Marketplace Provider`/`Client` are referenced by DocPerms but nothing grants them, and signup gives the Portal default role only.
5. No notifications of any kind for Marketplace records.

**Security defects (verified in code)**
- **S1** Guest has DocPerm `create` on Marketplace Inquiry (`marketplace_inquiry.json`) and `has_inquiry_permission` returns True for create. A guest can `POST /api/resource/Marketplace Inquiry` directly and **bypass the rate limit and the published-recipient check** in `submit_inquiry`.
- **S2** Proposal status is unguarded. The freelancer (`submitted_by`, Provider write) can set their own proposal to `Accepted`, and the client (Client write) can edit `cover_letter`/`proposed_amount`. A transition and field guard is needed in `MarketplaceProposal.validate`.
- **S3** Inquiry status is unguarded, and Provider write allows editing the requester's details.
- **S4** WP silently falls back to **fictional dummy data** whenever Frappe errors or returns non-200, including a genuine 404 (`class-marketplace-repository.php`). In production that can show fake accountants under real URLs. The fallback must be off whenever demo mode is off.
- **S5** Qdrant is unauthenticated and the embedding API runs over plain HTTP on a raw IP. Qdrant 4xx bodies are echoed to Guests through `frappe.throw` (`qdrant_client.py:_request`).
- **S6** The `accountants` Qdrant collection is shared with 20 unrelated real-looking records (name/phone/email). Isolation relies on a `status` filter; a dedicated collection is safer.
- **S7** A hard-coded login credential exists in `pre-edariba/src/services/paymentHMAC.js:14` (value not reproduced here). It should be rotated and removed. Unrelated to Marketplace, but found during the audit.

**Correctness defects**
- `list_*` apply `q` *after* pagination (`accountants.py`, `services.py`, `projects.py`), so `total` is wrong and pages come back sparse.
- WP fetches at most 50 rows and searches in PHP, so records past 50 are invisible.
- Search revalidation looks records up **by slug using `frappe_name`** (`search_service._PUBLIC_LOOKUP`). Names are fixed at insert while `slug` is editable, so any slug edit silently drops that record from search.
- Moderators fail the Service/Project `_guard_ownership` checks (only System Manager is exempt).
- `gateway.py` docstring references a non-existent `marketplace/api.py`.
- `/join` CTA (`marketplace-home.php:370`) points to a non-existent SPA route.
- Governorate has only 5 hard-coded options.

**Missing**: all authenticated Marketplace UI, workspace APIs, notification emails, response flow, and return-to-action through signup.

---

## H. Recommended Screen & Navigation Structure (pre-edariba)

```
Sidebar group "السوق" (new, in layouts/sidebar.vue)
├─ /marketplace/requests            الطلبات (tabs: الواردة | المُرسلة) — everyone
│   └─ /marketplace/requests/:id    تفاصيل الطلب + الرد/تغيير الحالة
├─ /marketplace/request/new         نموذج إرسال طلب (deep-link target from WP; not in sidebar)
├─ /marketplace/profile             ملفي المهني — providerOnly
├─ /marketplace/services            خدماتي — providerOnly
└─ (Phase B) /marketplace/proposals, /marketplace/projects, /marketplace/projects/:id/proposals
```
- Pages follow `ResellerDashboard.vue` (page → `ens.call('logic.marketplaceX')`) plus a small Pinia `MarketplaceStore` **without IndexedDB**. These are low-volume, user-scoped, server-paginated records, so the company-scoped IndexedDB rules don't apply; note this explicitly in code review.
- Routes carry `meta: { requiresAuth: true }` and are added to the onboarding-exempt list if J2 = exempt.
- Feedback goes through `notify.*`. Copy is Arabic-first (RTL) and uses Tajawal / IBM Plex Sans Arabic only.
- WP changes: replace the demo form and demo actions in `accountant-profile.php`, `service-detail.php`, `project-detail.php` with links built by a new helper `edariba_mp_app_url('request', [...])` (allowlisted route + slug); remove `initDemoForms` for them; fix `/join` → `/signup`.

---

## I. Implementation Roadmap

### Phase A — End-to-end MVP (request flow)
| # | Task | Files | Depends | Acceptance |
|---|---|---|---|---|
| A1 | Package the app (pyproject, patches.txt) and install on staging site of server.edariba.com | `eDariba-Marketplace/edariba_marketplace/pyproject.toml` | J1 | `bench --site staging migrate` clean; DocTypes visible |
| A2 | Add `requester` (Link User, RO) to Inquiry; remove Guest create DocPerm; guard status/requester fields | `marketplace_inquiry.json/.py`, `permissions.py` (requester can read own) | A1 | Guest `POST /api/resource/Marketplace Inquiry` → 403; requester sees own inquiry |
| A3 | Role assignment: grant `Marketplace Provider` when a Profile is created by or for a user; moderator verifies in Desk | `marketplace_profile.py` (`after_insert`), fixture for roles (`desk_access=0`) | A1 | Profile owner gets role; non-owner can't edit |
| A4 | Workspace API: `submit_request`, `list_requests`, `get_request`, `respond_request`, `set_request_status` with transition table and rate limit by user | new `api/public/workspace.py` | A2 | Unit tests per rule (§K) |
| A5 | Emails: new request → provider; response/status → requester. `frappe.sendmail(template=…, delayed=True)` from `after_insert`/`on_update` with a `notified_status` guard against duplicates | `marketplace_inquiry.py`, `templates/emails/marketplace_*.html` | A4 | Email Queue row created once per transition; save succeeds when SMTP is down |
| A6 | SPA: preserve redirect through guard and signup and set-password; `pendingIntent` | `router/index.js`, `pages/Auth/*.vue`, `services/logic.js` (`redirect_to`) | — | Logged-out deep link → signup/login → lands on form |
| A7 | SPA pages: request form, requests list (two tabs), request detail with respond; sidebar group | `pages/Marketplace/*.vue`, `stores/MarketplaceStore.js`, `services/logic.js`, `layouts/sidebar.vue`, router | A4, A6 | Manual E2E (§K) passes |
| A8 | WP: CTAs → app deep links; disable dummy fallback when not demo; fix `/join`; set `EDARIBA_FRAPPE_API_URL` on staging | plugin `class-marketplace-repository.php`, `helpers.php`, the three templates, `marketplace.js` | A1 | Real data renders; Frappe 404 → WP 404, never dummy |
| A9 | Fix server-side `q` filtering (push into SQL `like` filters before paginating) | `api/public/{accountants,services,projects}.py` | A1 | `total` matches |

### Phase B — Complete workflows
Provider profile editor and service CRUD (`/marketplace/profile`, `/marketplace/services` + `get/save_my_*`). Proposal API and screens with a transition guard (fixes S2). Project CRUD for clients. Marketplace items in the Header bell or unread badges. Moderator Desk workspace. Search lookup by `name` instead of slug (`search_service.py`).

### Phase C — Refinement
- Wire WP search/chat to `chat.discover` server-side with PHP fallback, and retire one of the duplicate intent routers.
- Qdrant API key + TLS for the embedding service; dedicated accountants collection (S5/S6).
- Scheduled `reconcile`.
- Email-failure dashboard (Email Queue `Error` status).
- Accessibility/RTL pass; governorate list completeness.
- Optional OIDC if WP personalization is needed.

---

## J. Risks & Decisions (need owner input)
- **J1** Install `edariba_marketplace` on **server.edariba.com** (same site as `accounting`)? *Recommended yes.* A separate site breaks the single-session model.
- **J2** Should a client who only wants to send a request be forced through ETA onboarding and company creation? *Recommended: exempt `/marketplace/*`.*
- **J3** Keep the **guest** inquiry form (lead capture, no account), or require login (brief's journey C)? *Recommended: require login*. If guest is kept, it must use only the hardened endpoint (S1 fix).
- **J4** Who is a "provider"? Any user with a Verified Profile, or only Reseller-plan tenants (`has_active_reseller_plan`)? This affects the sidebar flag and role grant.
- **J5** Does a request link to the requester's **tenant/company** (multi-tenancy invariant), or only to the User? *Recommended: User is authoritative; snapshot `requester_tenant` for context.*
- **J6** Request state model. *Recommended minimal model*: `New → Responded → Accepted | Declined → Closed`, with `Cancelled` by the requester before Accepted. Existing `Contacted` maps to `Responded`. Requires a Select options migration.
- **J7** Unpublished profile or service with open requests: *recommend* open requests remain readable to both parties; new requests are blocked (already enforced for recipient-published).
- **J8** EXPERTS_MARKETPLACE_MVP.md (concierge, no accountant login) conflicts with this build (accountant logins + self-service). Product must pick one for launch.
- Email capacity: Exim about 200/h per account. Fine for MVP; watch it if traffic grows.

---

## K. Test Plan (staging; nothing has been run yet)
- **Backend unit tests** (`bench --site staging run-tests --app edariba_marketplace`):
  - Guest cannot create an Inquiry through `/api/resource` (S1).
  - `submit_request` sets `requester` from the session and ignores a client-supplied value.
  - Rejects an unpublished/unverified recipient, a service of another provider, and requests to self.
  - Rate limit holds.
  - Duplicate open request is blocked.
  - Status transitions: allowed vs forbidden per role.
  - Proposal self-accept is forbidden (S2).
  - List visibility: provider sees received only, requester sees sent only, third party sees nothing.
  - Email: one Email Queue row per transition; re-saving does not resend; the save commits when the SMTP account is disabled.
- **Indexing**: publish → point appears; unpublish → point deleted; search never returns an unpublished doc (stub Qdrant/embeddings; **never touch production collections**).
- **SPA**:
  - Vitest specs for the redirect guard, `pendingIntent`, and redirect allowlist (rejects `//evil`, `https://…`).
  - Playwright: logged-out deep link → login → form pre-filled → submit → appears in "المُرسلة".
  - Second account (provider) sees it in "الواردة" and responds; requester sees the response.
- **WP**:
  - Staging with `EDARIBA_FRAPPE_API_URL` set and demo mode off: real records render; unknown slug → 404 (not dummy); Frappe down → error/empty state (not dummy).
  - CTAs produce correct app URLs.
- **Manual security checks**:
  - Tamper with `recipient`/`requester` in DevTools.
  - Call Desk REST endpoints directly as Provider/Client.
  - Confirm email links contain only the record id.

**Verification of this report**: every [V] claim cites a file. [U] items (deployment site, wp-config value, CORS/cookie site_config, Frappe version, email capacity, whether the README's live Qdrant tests are reproducible) must be confirmed on the server before Phase A starts.
