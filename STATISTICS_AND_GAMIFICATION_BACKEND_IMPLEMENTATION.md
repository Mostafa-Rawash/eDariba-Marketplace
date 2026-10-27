# Statistics and Gamification: backend implementation

Date: 2026-10-26. Backend only (`eDariba-Marketplace`). No Vue, WordPress or styling changes were made in this task. Nothing has run on a bench or a site yet. Every item below is **implemented in code but not executed on a site**, except the pure-Python rules, which have passing unit tests.

## 1. Verification: verified by default (temporary)

- **One switch:** `marketplace/services/verification.py`. It reads `marketplace_verification_required` from `site_config.json` and defaults to off.
- **New profiles** start `Verified` with `verification_method = "Automatic"` and `verified_at` set, whatever the client sent.
- **Pending profiles** become Verified on their next save. The patch `verify_profiles_by_default` backfills existing Pending profiles. It also marks earlier self-verified profiles as `Automatic`, because nobody reviewed them. Rejected profiles are not touched. The patch can be re-run safely, and it skips itself when verification is required.
- **Who can change it:** only moderators (System Manager, Marketplace Moderator) can change `verification_status`. A moderator setting Verified records `verification_method = "Moderator"`. Owners get a PermissionError through any API.
- **Services** have no verification field. A service is as verified as its provider's profile. Nothing in the backend gates requests, services or proposals on verification.
- **To re-enable verification:** set `"marketplace_verification_required": 1`. Optionally reset the automatic ones with `UPDATE ... SET verification_status='Pending' WHERE verification_method='Automatic'`, as written in `verification.py`. Then build the moderator review screen and bind every badge to `Verified`.

## 2. Integrity fixes

- **Protected profile fields:** `user`, `slug`, `previous_slugs`, `verification_method`, `verified_at`, `published_at` and `company` can't be changed by non-moderators (controller guard). On projects, `accepted_proposal` and `closed_at` are server-set only.
- **Proposal actions** go through the new `api/proposals.py`:
  - `set_proposal_status(name, status)` and `withdraw_proposal(name)`.
  - The transition table is in `services/proposal_rules.py`. The client shortlists, accepts or rejects while the project is Published; the freelancer withdraws an active proposal. Anyone else gets "not found".
  - Accepting locks the project row, refuses a second accept, closes the project (`closed_at`, `accepted_proposal`) and rejects the other active proposals.
  - The controller refuses status changes made outside this API, except by a System Manager.
- **Proposal guards on submit:**
  - the project must be Published and not past its deadline;
  - the cover letter must be 80–2000 visible characters;
  - at most 10 proposals per hour per user;
  - the profile row is locked against concurrent duplicates.
  - The messages match the ones the app already maps.
- **Privacy:**
  - Guest DocPerm is removed from Profile, Service and Project. The public site reads through `api/public/*` with field allowlists.
  - On single-document reads, `owner`, `modified_by` and the profile's `company` are blanked for anyone but the record's owner and moderators (`services/privacy.py`).
- **Service count:** `get_accountant` now returns `published_services_total`. The list still holds the first 20.

## 3. Lifecycle timestamps

- **Requests (Inquiry):** `first_responded_at`, `accepted_at`, `declined_at`, `closed_at`, `cancelled_at`, `closed_by`. They're set in the controller, once, and never overwritten. `responded_at` keeps meaning "latest reply".
  - The patch `backfill_inquiry_lifecycle` fills old rows only from Version history. It guesses nothing.
- **Proposals:** `shortlisted_at`, `accepted_at`, `rejected_at`, `withdrawn_at`.
- **Projects:** `closed_at`, `accepted_proposal`.

## 4. Statistics

- **Collection:**
  - **Doctypes:** `Marketplace Activity` (raw, purged after 90 days by a daily job) and `Marketplace Daily Metric` (SQL-upserted counters).
  - **Endpoint:** `api/public/events.track` (also gateway `event/track`).
  - **Views:** profile and service views. Unique visitors are counted per day through an HMAC that rotates daily. No IP or cookie is stored. Bots, owners and moderators are excluded. Each visitor is limited to 30 events a minute, and each IP to 120 a minute.
  - **Searches:** the list endpoints (first page with `q`) and semantic search log search volume, no-result searches and per-result impressions, and return `meta.search_id`. A click counts only for a result that search returned, within 24h, once per visitor.
- **Endpoints (`api/stats.py`):**
  - `provider_stats` (own profile only): requests by status, response rate (answered within 48h), median first-response time, completion, cancellation and decline rates, proposal acceptance rate, median time to acceptance, views, unique visitor-days, impressions, clicks, CTR and completeness.
  - `profile_completion`.
  - `admin_stats` (moderators): users by type, status and role; profiles, services and projects by status; requests, proposals, activity, no-result queries (shown only when seen at least twice), marketplace Error Log counts and points.
  - Dates are inclusive, 90 days by default, 366 at most.
  - Rates are `null` below a sample of 5 (CTR below 20).
  - Activity numbers carry `collected_since`: nothing before deployment is presented as history.
- **Formulas:** `services/stats_formulas.py`. Completeness: `services/profile_completion.py`. The publish gate uses the same module with an unchanged rule.

## 5. Gamification

- **Points ledger:** `Marketplace Points Entry` is append-only (edit and delete are refused). Every entry has a unique `idempotency_key`.
- **Awarding:** `services/gamification.py` `award()` is the only writer, and no API takes a points value.
- **Rules** (`services/gamification_rules.py`; site config may change values but not add events):
  - profile completed: 50, once per user;
  - service published: 10, at most 3 a day;
  - first response to a request: 5, at most 10 a day;
  - request closed after acceptance: 20, at most 5 a day;
  - proposal accepted: 15, at most 5 a day.
  - Set `marketplace_gamification_enabled: 0` to turn awarding off.
- **Achievements:** `Marketplace Achievement` holds the definitions (seeded by a patch), and `Marketplace User Achievement` is unique per user and achievement. They're evaluated on the server after each award.
- **Read-only endpoints:** `api/gamification.my_points` and `my_achievements`.
- **Separate from verification:** nothing here reads or writes verification. There are no leaderboards, challenges or money.

## 6. Files

- **New:**
  - `services/`: `verification.py`, `proposal_rules.py`, `profile_completion.py`, `stats_formulas.py`, `stats.py`, `event_rules.py`, `events.py`, `privacy.py`, `gamification_rules.py`, `gamification.py`.
  - `api/`: `proposals.py`, `stats.py`, `gamification.py`, `public/events.py`.
  - Patches `verify_profiles_by_default`, `backfill_inquiry_lifecycle`, `seed_marketplace_achievements`.
  - Five doctypes: Activity, Daily Metric, Points Entry, Achievement, User Achievement.
- **Changed:**
  - Controllers and JSON for Profile, Proposal, Inquiry, Project and Service. Guest perms are removed from Profile, Service and Project.
  - `api/workspace.py` (`closed_by`), `api/gateway.py`, public list and search endpoints, `repository.py`, `hooks.py` (doc_events and a daily scheduler job), `permissions.py` comments, `patches.txt`.

## 7. Tests

- **Ran here:** `python -m unittest` on the 9 pure modules: 71 tests, all OK. 58 are new (verification, proposal rules, completeness, stats formulas, event rules, gamification rules, backfill parsing), plus the 13 existing ones.
- **Written, not run** (they need `bench run-tests`):
  - `services/tests/test_marketplace_integration.py`: proposal workflow and authorization, single accept, ledger idempotency, caps and append-only, achievements, view dedupe, click validation, privacy masking, service count beyond 20.
  - Updated profile verification tests and new proposal guard tests.

## 8. Needs frontend or WordPress work later

- **Proposal actions:** `pre-edariba` must call `api/proposals.*` instead of `updateDoc` for proposal status (today those writes fail).
- **Resubmit:** the "resubmit" button on Rejected profiles no longer works while verification is bypassed.
- **Service count:** WordPress must show `published_services_total`.
- **Tracking:** WordPress must send `event/track` with a first-party visitor cookie and the user agent on profile and service pages, and pass `search_id` on result clicks. Its response cache (300s) undercounts identical searches.
- **Screens:** "إحصائياتي", points, achievements and the admin dashboard.
- **Badges:** "معتمد" now means automatically verified. The hard-coded counters on the public site are still hard-coded.
- **List reads:** logged-in users can still request `owner` in `/api/resource` *list* calls. Closing that needs the app to read the directory through `api/public/*`, then removing Invoicing Owner read.

## 9. Not implemented

- Reviews and ratings, payments and revenue, notifications to other bidders on hire, engagement entities, leaderboards and challenges.
- Per-service request statistics, repeat clients, and backfilling `closed_by`.
- Activity statistics start at deployment.
