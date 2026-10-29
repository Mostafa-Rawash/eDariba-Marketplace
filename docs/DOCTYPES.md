# Marketplace DocTypes

Generated from the DocType JSON definitions in `marketplace/<module>/doctype/` by `scripts/gen_doctypes.py`. Regenerate after schema changes rather than editing by hand.

14 DocTypes.

| DocType | Module | Naming | Child table | Fields |
|---|---|---|---|---|
| [Marketplace Achievement](#marketplace-achievement) | Gamification | field:code | No | 7 |
| [Marketplace Activity](#marketplace-activity) | Activity | hash | No | 12 |
| [Marketplace Category](#marketplace-category) | Marketplace | field:slug | No | 4 |
| [Marketplace Daily Metric](#marketplace-daily-metric) | Activity | hash | No | 6 |
| [Marketplace Inquiry](#marketplace-inquiry) | Inquiries | hash | No | 19 |
| [Marketplace Points Entry](#marketplace-points-entry) | Gamification | hash | No | 8 |
| [Marketplace Profile](#marketplace-profile) | Marketplace | field:slug | No | 23 |
| [Marketplace Project](#marketplace-project) | Freelance | field:slug | No | 18 |
| [Marketplace Proposal](#marketplace-proposal) | Freelance | hash | No | 13 |
| [Marketplace Qualification](#marketplace-qualification) | Marketplace |  | Yes | 3 |
| [Marketplace Service](#marketplace-service) | Marketplace | field:slug | No | 12 |
| [Marketplace Specialty](#marketplace-specialty) | Marketplace | field:title | No | 4 |
| [Marketplace Tag](#marketplace-tag) | Marketplace |  | Yes | 1 |
| [Marketplace User Achievement](#marketplace-user-achievement) | Gamification | hash | No | 4 |

## Marketplace Achievement

Achievement definitions: reached when the user's metric (gamification/rules.METRICS) is at least threshold. Evaluated on the server (gamification/service.py).

- **Module:** `Gamification`
- **Naming:** `field:code`

| Fieldname | Label | Type | Options | Required | Unique | Default | In list | Read only | Level |
|---|---|---|---|---|---|---|---|---|---|
| `code` | Code | Data |  | ✓ | ✓ |  | ✓ |  |  |
| `title` | Title | Data |  | ✓ |  |  | ✓ |  |  |
| `description` | Description | Small Text |  |  |  |  |  |  |  |
| `metric` | Metric | Select | profile_complete, services_published, requests_responded, requests_completed, proposals_accepted, points_total | ✓ |  |  | ✓ |  |  |
| `threshold` | Threshold | Int |  | ✓ |  | 1 | ✓ |  |  |
| `is_active` | Is Active | Check |  |  |  | 1 | ✓ |  |  |
| `sort_order` | Sort Order | Int |  |  |  | 0 |  |  |  |

**Permissions**

| Role | Level | Read | Write | Create | Delete | If owner |
|---|---|---|---|---|---|---|
| System Manager | 0 | ✓ | ✓ | ✓ | ✓ |  |
| Marketplace Moderator | 0 | ✓ |  |  |  |  |

## Marketplace Activity

Raw marketplace activity: unique daily profile/service views, searches and search-result clicks (activity/events.py). Visitors are stored only as a daily-rotating HMAC (visitor_hash); no IP, cookie or guest identity. Rows older than the retention period (default 90 days) are purged daily; daily totals live in Marketplace Daily Metric.

- **Module:** `Activity`
- **Naming:** `hash`

| Fieldname | Label | Type | Options | Required | Unique | Default | In list | Read only | Level |
|---|---|---|---|---|---|---|---|---|---|
| `event_type` | Event Type | Select | profile_view, service_view, search, search_click | ✓ |  |  | ✓ |  |  |
| `event_date` | Event Date | Date |  | ✓ |  |  | ✓ |  |  |
| `occurred_at` | Occurred At | Datetime |  | ✓ |  |  |  |  |  |
| `reference_doctype` | Reference DocType | Link | DocType |  |  |  |  |  |  |
| `reference_name` | Reference Name | Data |  |  |  |  | ✓ |  |  |
| `visitor_hash` | Visitor Hash | Data |  |  |  |  |  |  |  |
| `dedupe_key` | Dedupe Key | Data |  |  | ✓ |  |  |  |  |
| `query_text` | Query | Data |  |  |  |  |  |  |  |
| `entity_types` | Entity Types | Data |  |  |  |  |  |  |  |
| `result_count` | Result Count | Int |  |  |  |  |  |  |  |
| `result_refs` | Result Refs | Small Text |  |  |  |  |  |  |  |
| `search` | Search | Link | Marketplace Activity |  |  |  |  |  |  |

**Permissions**

| Role | Level | Read | Write | Create | Delete | If owner |
|---|---|---|---|---|---|---|
| System Manager | 0 | ✓ |  |  | ✓ |  |
| Marketplace Moderator | 0 | ✓ |  |  |  |  |

## Marketplace Category

Shared category taxonomy used to filter accountants, services, and projects. One list across all three entities — Dummy_Data_Provider::service_categories() is used identically by accountants, services, and projects in the current WordPress code, so a single shared taxonomy is correct rather than three near-duplicate ones.

- **Module:** `Marketplace`
- **Naming:** `field:slug`
- **Track changes:** `Yes`
- **Sort:** `sort_order ASC`

| Fieldname | Label | Type | Options | Required | Unique | Default | In list | Read only | Level |
|---|---|---|---|---|---|---|---|---|---|
| `title` | Title | Data |  | ✓ |  |  | ✓ |  |  |
| `slug` | Slug | Data |  | ✓ | ✓ |  | ✓ |  |  |
| `is_active` | Is Active | Check |  |  |  | 1 | ✓ |  |  |
| `sort_order` | Sort Order | Int |  |  |  | 0 |  |  |  |

**Permissions**

| Role | Level | Read | Write | Create | Delete | If owner |
|---|---|---|---|---|---|---|
| System Manager | 0 | ✓ | ✓ | ✓ | ✓ |  |
| Marketplace Moderator | 0 | ✓ | ✓ | ✓ |  |  |
| Guest | 0 | ✓ |  |  |  |  |

## Marketplace Daily Metric

Daily counters per metric and record (activity/events.py, upserted with SQL): profile_view, service_view (all views), search_impression, search_click (per result), search and search_no_result (site-wide, no reference). Kept after raw activity is purged.

- **Module:** `Activity`
- **Naming:** `hash`

| Fieldname | Label | Type | Options | Required | Unique | Default | In list | Read only | Level |
|---|---|---|---|---|---|---|---|---|---|
| `metric_key` | Metric Key | Data |  | ✓ | ✓ |  |  |  |  |
| `metric` | Metric | Data |  | ✓ |  |  | ✓ |  |  |
| `metric_date` | Date | Date |  | ✓ |  |  | ✓ |  |  |
| `reference_doctype` | Reference DocType | Link | DocType |  |  |  |  |  |  |
| `reference_name` | Reference Name | Data |  |  |  |  | ✓ |  |  |
| `count` | Count | Int |  |  |  | 0 | ✓ |  |  |

**Permissions**

| Role | Level | Read | Write | Create | Delete | If owner |
|---|---|---|---|---|---|---|
| System Manager | 0 | ✓ |  |  | ✓ |  |
| Marketplace Moderator | 0 | ✓ |  |  |  |  |

## Marketplace Inquiry

A request from a logged-in client to one accountant (Marketplace Profile). Created only through marketplace.inquiries.api.submit_request; users have no DocPerm on it. Fully private.

- **Module:** `Inquiries`
- **Naming:** `hash`
- **Track changes:** `Yes`

| Fieldname | Label | Type | Options | Required | Unique | Default | In list | Read only | Level |
|---|---|---|---|---|---|---|---|---|---|
| `recipient` | Recipient | Link | Marketplace Profile | ✓ |  |  | ✓ |  |  |
| `related_service` | Related Service | Link | Marketplace Service |  |  |  |  |  |  |
| _Requester_ (Section Break) | | | | | | | | | |
| `requester` | Requester | Link | User | ✓ |  |  |  | ✓ |  |
| `requester_name` | Requester Name | Data |  | ✓ |  |  |  |  |  |
| `requester_email` | Requester Email | Data | Email | ✓ |  |  |  |  |  |
| `requester_phone` | Requester Phone | Data |  |  |  |  |  |  |  |
| `inquiry_type` | Inquiry Type | Select | tax_audit, einvoice, annual_return, consultation |  |  |  |  |  |  |
| `details` | Details | Small Text |  | ✓ |  |  |  |  |  |
| _Status_ (Section Break) | | | | | | | | | |
| `status` | Status | Select | New, Responded, Accepted, Declined, Closed, Cancelled |  |  | New | ✓ | ✓ |  |
| `created_at` | Created At | Datetime |  |  |  |  |  | ✓ |  |
| _Response_ (Section Break) | | | | | | | | | |
| `response` | Response | Small Text |  |  |  |  |  | ✓ |  |
| `responded_at` | Responded At | Datetime |  |  |  |  |  | ✓ |  |
| `first_responded_at` | First Responded At | Datetime |  |  |  |  |  | ✓ |  |
| `accepted_at` | Accepted At | Datetime |  |  |  |  |  | ✓ |  |
| `declined_at` | Declined At | Datetime |  |  |  |  |  | ✓ |  |
| `closed_at` | Closed At | Datetime |  |  |  |  |  | ✓ |  |
| `cancelled_at` | Cancelled At | Datetime |  |  |  |  |  | ✓ |  |
| `closed_by` | Closed By | Select | requester, provider, support |  |  |  |  | ✓ |  |
| `support_note` | Support Note | Small Text |  |  |  |  |  | ✓ |  |

**Permissions**

| Role | Level | Read | Write | Create | Delete | If owner |
|---|---|---|---|---|---|---|
| System Manager | 0 | ✓ | ✓ | ✓ | ✓ |  |
| Marketplace Moderator | 0 | ✓ |  |  |  |  |

## Marketplace Points Entry

Append-only points ledger (gamification/service.py). Points are awarded only by the server for events it verifies; idempotency_key makes each award happen once. Entries are never edited: a correction is a new entry by a System Manager.

- **Module:** `Gamification`
- **Naming:** `hash`

| Fieldname | Label | Type | Options | Required | Unique | Default | In list | Read only | Level |
|---|---|---|---|---|---|---|---|---|---|
| `user` | User | Link | User | ✓ |  |  | ✓ |  |  |
| `points` | Points | Int |  | ✓ |  |  | ✓ |  |  |
| `event_type` | Event Type | Data |  | ✓ |  |  | ✓ |  |  |
| `reference_doctype` | Reference DocType | Link | DocType |  |  |  |  |  |  |
| `reference_name` | Reference Name | Dynamic Link | reference_doctype |  |  |  |  |  |  |
| `idempotency_key` | Idempotency Key | Data |  | ✓ | ✓ |  |  |  |  |
| `awarded_at` | Awarded At | Datetime |  | ✓ |  |  | ✓ |  |  |
| `note` | Note | Small Text |  |  |  |  |  |  |  |

**Permissions**

| Role | Level | Read | Write | Create | Delete | If owner |
|---|---|---|---|---|---|---|
| System Manager | 0 | ✓ |  | ✓ |  |  |
| Marketplace Moderator | 0 | ✓ |  |  |  |  |

## Marketplace Profile

Professional profile for an accountant or accounting firm, shown by card-accountant.php and accountant-profile.php. One profile per Frappe User (app.edariba login identity); this is NOT the User record itself and does not duplicate auth/credential fields. 'verified'/'stats'/'reviews'/'ledger_id'/'membership'/'languages'/'hourly_rate'/'response_time' were already removed from the live UI in a prior pass and are intentionally not modeled.

- **Module:** `Marketplace`
- **Naming:** `field:slug`
- **Title field:** `display_name`
- **Track changes:** `Yes`

| Fieldname | Label | Type | Options | Required | Unique | Default | In list | Read only | Level |
|---|---|---|---|---|---|---|---|---|---|
| `user` | User | Link | User | ✓ | ✓ | __user |  |  | 1 |
| `company` | Company | Link | Company |  |  |  |  |  |  |
| `profile_type` | Profile Type | Select | Individual, Firm | ✓ |  | Individual | ✓ |  |  |
| `display_name` | Display Name | Data |  | ✓ |  |  | ✓ |  |  |
| `slug` | Slug | Data |  | ✓ | ✓ |  | ✓ |  |  |
| `previous_slugs` | Previous Slugs | Small Text |  |  |  |  |  | ✓ |  |
| `headline` | Headline | Data |  | ✓ |  |  | ✓ |  |  |
| `governorate` | Governorate | Select | القاهرة, الجيزة, الإسكندرية, الشرقية, الدقهلية | ✓ |  |  | ✓ |  |  |
| `area` | Area / District | Data |  |  |  |  |  |  |  |
| `experience_years` | Years of Experience | Int |  | ✓ |  |  | ✓ |  |  |
| _Profile_ (Section Break) | | | | | | | | | |
| `avatar` | Avatar | Attach Image |  |  |  |  |  |  |  |
| `bio` | Bio | Text Editor |  | ✓ |  |  |  |  |  |
| `specialties` | Specialties | Table | Marketplace Tag |  |  |  |  |  |  |
| `qualifications` | Qualifications | Table | Marketplace Qualification |  |  |  |  |  |  |
| _Case Study (optional)_ (Section Break) | | | | | | | | | |
| `case_study_title` | Case Study Title | Data |  |  |  |  |  |  |  |
| `case_study_text` | Case Study Text | Small Text |  |  |  |  |  |  |  |
| _Marketplace Roles_ (Section Break) | | | | | | | | | |
| `offers_services` | Offers Services | Check |  |  |  | 1 |  |  |  |
| `accepts_projects` | Accepts Projects | Check |  |  |  | 1 |  |  |  |
| _Status_ (Section Break) | | | | | | | | | |
| `verification_status` | Verification Status | Select | Pending, Verified, Rejected |  |  | Verified | ✓ |  |  |
| `verification_method` | Verification Method | Select | Automatic, Moderator |  |  |  |  | ✓ |  |
| `verified_at` | Verified At | Datetime |  |  |  |  |  | ✓ |  |
| `publication_status` | Publication Status | Select | Draft, Published, Unpublished |  |  | Draft | ✓ |  |  |
| `published_at` | Published At | Datetime |  |  |  |  |  | ✓ |  |

**Permissions**

| Role | Level | Read | Write | Create | Delete | If owner |
|---|---|---|---|---|---|---|
| System Manager | 0 | ✓ | ✓ | ✓ | ✓ |  |
| Marketplace Moderator | 0 | ✓ |  |  |  |  |
| System Manager | 1 | ✓ | ✓ |  |  |  |
| Marketplace Moderator | 1 | ✓ |  |  |  |  |
| Invoicing Owner | 0 | ✓ | ✓ | ✓ |  |  |

## Marketplace Project

A freelance project posted by a client, shown by card-project.php, project-detail.php, and the projects.php catalog. 'proposals_count' was already removed from the live UI in a prior pass (it is now derived by counting Marketplace Proposal rows, not stored).

- **Module:** `Freelance`
- **Naming:** `field:slug`
- **Title field:** `title`
- **Track changes:** `Yes`

| Fieldname | Label | Type | Options | Required | Unique | Default | In list | Read only | Level |
|---|---|---|---|---|---|---|---|---|---|
| `title` | Title | Data |  | ✓ |  |  | ✓ |  |  |
| `slug` | Slug | Data |  | ✓ | ✓ |  | ✓ |  |  |
| `category` | Category | Link | Marketplace Category | ✓ |  |  | ✓ |  |  |
| `client` | Client | Link | User | ✓ |  | __user |  |  | 1 |
| `client_display_name` | Client Display Name | Data |  | ✓ |  |  |  |  |  |
| `client_type` | Client Type | Select | شركة ناشئة, منشأة صغيرة, شركة متوسطة, شركة قيد التأسيس, مجموعة شركات, منظمة غير ربحية | ✓ |  |  | ✓ |  |  |
| _Brief_ (Section Break) | | | | | | | | | |
| `description` | Description | Text Editor |  | ✓ |  |  |  |  |  |
| `required_skills` | Required Skills | Table | Marketplace Tag |  |  |  |  |  |  |
| _Budget & Deadline_ (Section Break) | | | | | | | | | |
| `budget_min` | Budget Min | Currency |  | ✓ |  |  | ✓ |  |  |
| `budget_max` | Budget Max | Currency |  | ✓ |  |  | ✓ |  |  |
| `currency` | Currency | Data |  | ✓ |  | ج.م |  |  |  |
| `deadline` | Deadline | Date |  | ✓ |  |  | ✓ |  |  |
| `escrow` | Escrow Protected | Check |  |  |  | 1 |  |  |  |
| _Status_ (Section Break) | | | | | | | | | |
| `publication_status` | Publication Status | Select | Draft, Published, Closed, Archived |  |  | Draft | ✓ |  |  |
| `published_at` | Published At | Datetime |  |  |  |  |  | ✓ |  |
| `closed_at` | Closed At | Datetime |  |  |  |  |  | ✓ |  |
| `accepted_proposal` | Accepted Proposal | Link | Marketplace Proposal |  |  |  |  | ✓ |  |
| `support_note` | Support Note | Small Text |  |  |  |  |  | ✓ |  |

**Permissions**

| Role | Level | Read | Write | Create | Delete | If owner |
|---|---|---|---|---|---|---|
| System Manager | 0 | ✓ | ✓ | ✓ | ✓ |  |
| Marketplace Moderator | 0 | ✓ |  |  |  |  |
| System Manager | 1 | ✓ | ✓ |  |  |  |
| Marketplace Moderator | 1 | ✓ |  |  |  |  |
| Invoicing Owner | 0 | ✓ | ✓ | ✓ |  |  |

## Marketplace Proposal

ASSUMPTION / NOT YET IN THE WORDPRESS UI: project-detail.php's 'تقديم عرض على المشروع' button is an honest demo redirect to app.edariba with no proposal form on the public site today (data-edariba-demo-action). This DocType is still required because the product brief explicitly states freelancers submit proposals to projects (Mostaql-style) as one of the three core offerings, and app.edariba (not WordPress) is where that authenticated flow lives. Field set below is the minimum any such flow needs; confirm against the actual app.edariba form before building UI on top of it. Fully private: no Guest access anywhere.

- **Module:** `Freelance`
- **Naming:** `hash`
- **Track changes:** `Yes`

| Fieldname | Label | Type | Options | Required | Unique | Default | In list | Read only | Level |
|---|---|---|---|---|---|---|---|---|---|
| `project` | Project | Link | Marketplace Project | ✓ |  |  | ✓ |  |  |
| `freelancer` | Freelancer | Link | Marketplace Profile | ✓ |  |  | ✓ |  |  |
| `submitted_by` | Submitted By | Link | User | ✓ |  |  |  | ✓ |  |
| `proposed_amount` | Proposed Amount | Currency |  | ✓ |  |  | ✓ |  |  |
| `currency` | Currency | Data |  | ✓ |  | ج.م |  |  |  |
| `estimated_days` | Estimated Days | Int |  |  |  |  |  |  |  |
| _Cover Letter_ (Section Break) | | | | | | | | | |
| `cover_letter` | Cover Letter | Text Editor |  | ✓ |  |  |  |  |  |
| _Status_ (Section Break) | | | | | | | | | |
| `status` | Status | Select | Submitted, Shortlisted, Accepted, Rejected, Withdrawn |  |  | Submitted | ✓ |  |  |
| `submitted_at` | Submitted At | Datetime |  |  |  |  |  | ✓ |  |
| `shortlisted_at` | Shortlisted At | Datetime |  |  |  |  |  | ✓ |  |
| `accepted_at` | Accepted At | Datetime |  |  |  |  |  | ✓ |  |
| `rejected_at` | Rejected At | Datetime |  |  |  |  |  | ✓ |  |
| `withdrawn_at` | Withdrawn At | Datetime |  |  |  |  |  | ✓ |  |

**Permissions**

| Role | Level | Read | Write | Create | Delete | If owner |
|---|---|---|---|---|---|---|
| System Manager | 0 | ✓ | ✓ | ✓ | ✓ |  |
| Marketplace Moderator | 0 | ✓ |  |  |  |  |
| Invoicing Owner | 0 | ✓ |  | ✓ |  |  |

## Marketplace Qualification

Child table backing Marketplace Profile.qualifications. Mirrors the 'title'/'issuer'/'year' keys in each accountant's qualifications array (class-dummy-data-provider.php) and the credential cards rendered in accountant-profile.php. The 'code' key that used to exist there was removed from the UI, so it is intentionally not modeled here.

- **Module:** `Marketplace`
- **Child table:** `Yes`

| Fieldname | Label | Type | Options | Required | Unique | Default | In list | Read only | Level |
|---|---|---|---|---|---|---|---|---|---|
| `title` | Title | Data |  | ✓ |  |  | ✓ |  |  |
| `issuer` | Issuer | Data |  | ✓ |  |  | ✓ |  |  |
| `year` | Year | Data |  |  |  |  | ✓ |  |  |

## Marketplace Service

A fixed-price service package published by a provider, shown by card-service.php, services.php, and service-detail.php. 'rating'/'reviews_count'/'delivery_days' were already removed from the live UI in a prior pass and are intentionally not modeled.

- **Module:** `Marketplace`
- **Naming:** `field:slug`
- **Title field:** `title`
- **Track changes:** `Yes`

| Fieldname | Label | Type | Options | Required | Unique | Default | In list | Read only | Level |
|---|---|---|---|---|---|---|---|---|---|
| `title` | Title | Data |  | ✓ |  |  | ✓ |  |  |
| `slug` | Slug | Data |  | ✓ | ✓ |  | ✓ |  |  |
| `provider` | Provider | Link | Marketplace Profile | ✓ |  |  | ✓ |  |  |
| `category` | Category | Link | Marketplace Category |  |  |  | ✓ |  |  |
| `price` | Price | Currency |  |  |  |  | ✓ |  |  |
| `currency` | Currency | Data |  | ✓ |  | ج.م |  |  |  |
| `price_unit` | Price Unit | Select | Total, Monthly, Per Session | ✓ |  | Total |  |  |  |
| _Content_ (Section Break) | | | | | | | | | |
| `description` | Description | Text Editor |  |  |  |  |  |  |  |
| `badges` | Badges | Table | Marketplace Tag |  |  |  |  |  |  |
| `features` | Features | Table | Marketplace Tag |  |  |  |  |  |  |
| _Status_ (Section Break) | | | | | | | | | |
| `publication_status` | Publication Status | Select | Draft, Published, Unpublished |  |  | Draft | ✓ |  |  |
| `published_at` | Published At | Datetime |  |  |  |  |  | ✓ |  |

**Permissions**

| Role | Level | Read | Write | Create | Delete | If owner |
|---|---|---|---|---|---|---|
| System Manager | 0 | ✓ | ✓ | ✓ | ✓ |  |
| Marketplace Moderator | 0 | ✓ |  |  |  |  |
| Invoicing Owner | 0 | ✓ | ✓ | ✓ | ✓ |  |

## Marketplace Specialty

The list accountants pick their specialties from on their profile («التخصصات الدقيقة»). A profile stores the chosen titles in its specialties table (Marketplace Tag.label), so search and the WordPress site read them as before. Each specialty may belong to a Marketplace Category, which the app uses to group the list.

- **Module:** `Marketplace`
- **Naming:** `field:title`
- **Track changes:** `Yes`
- **Sort:** `sort_order ASC`

| Fieldname | Label | Type | Options | Required | Unique | Default | In list | Read only | Level |
|---|---|---|---|---|---|---|---|---|---|
| `title` | Title | Data |  | ✓ | ✓ |  | ✓ |  |  |
| `category` | Category | Link | Marketplace Category |  |  |  | ✓ |  |  |
| `is_active` | Is Active | Check |  |  |  | 1 | ✓ |  |  |
| `sort_order` | Sort Order | Int |  |  |  | 0 |  |  |  |

**Permissions**

| Role | Level | Read | Write | Create | Delete | If owner |
|---|---|---|---|---|---|---|
| System Manager | 0 | ✓ | ✓ | ✓ | ✓ |  |
| Marketplace Moderator | 0 | ✓ | ✓ | ✓ |  |  |
| Guest | 0 | ✓ |  |  |  |  |

## Marketplace Tag

Generic free-text label row, reused as the child table behind Marketplace Profile.specialties, Marketplace Service.badges, Marketplace Service.features, and Marketplace Project.required_skills. These are rendered as plain tag chips in the current WordPress templates (array_slice($acc['specialties'],0,4) etc.) with no controlled vocabulary or cross-entity lookup today, so one reusable free-text child doctype is correct instead of four near-identical ones or a premature taxonomy Link.

- **Module:** `Marketplace`
- **Child table:** `Yes`

| Fieldname | Label | Type | Options | Required | Unique | Default | In list | Read only | Level |
|---|---|---|---|---|---|---|---|---|---|
| `label` | Label | Data |  | ✓ |  |  | ✓ |  |  |

## Marketplace User Achievement

A user reaching an achievement. Created only by the server (gamification/service.py); unique per user and achievement.

- **Module:** `Gamification`
- **Naming:** `hash`

| Fieldname | Label | Type | Options | Required | Unique | Default | In list | Read only | Level |
|---|---|---|---|---|---|---|---|---|---|
| `user` | User | Link | User | ✓ |  |  | ✓ |  |  |
| `achievement` | Achievement | Link | Marketplace Achievement | ✓ |  |  | ✓ |  |  |
| `achieved_at` | Achieved At | Datetime |  | ✓ |  |  | ✓ |  |  |
| `unique_key` | Unique Key | Data |  | ✓ | ✓ |  |  |  |  |

**Permissions**

| Role | Level | Read | Write | Create | Delete | If owner |
|---|---|---|---|---|---|---|
| System Manager | 0 | ✓ |  |  | ✓ |  |
| Marketplace Moderator | 0 | ✓ |  |  |  |  |
