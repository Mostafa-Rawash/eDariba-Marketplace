# Marketplace DocTypes

Generated from the DocType JSON definitions in `marketplace/marketplace/doctype/` by `scripts/gen_doctypes.py`. Regenerate after schema changes rather than editing by hand.

8 DocTypes.

| DocType | Module | Naming | Child table | Fields |
|---|---|---|---|---|
| [Marketplace Category](#marketplace-category) | Marketplace | field:slug | No | 4 |
| [Marketplace Inquiry](#marketplace-inquiry) | Marketplace | hash | No | 12 |
| [Marketplace Profile](#marketplace-profile) | Marketplace | field:slug | No | 20 |
| [Marketplace Project](#marketplace-project) | Marketplace | field:slug | No | 15 |
| [Marketplace Proposal](#marketplace-proposal) | Marketplace | hash | No | 9 |
| [Marketplace Qualification](#marketplace-qualification) | Marketplace |  | Yes | 3 |
| [Marketplace Service](#marketplace-service) | Marketplace | field:slug | No | 12 |
| [Marketplace Tag](#marketplace-tag) | Marketplace |  | Yes | 1 |

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

## Marketplace Inquiry

A request from a logged-in client to one accountant (Marketplace Profile). Created only through marketplace.api.workspace.submit_request; users have no DocPerm on it. Fully private.

- **Module:** `Marketplace`
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

**Permissions**

| Role | Level | Read | Write | Create | Delete | If owner |
|---|---|---|---|---|---|---|
| System Manager | 0 | ✓ | ✓ | ✓ | ✓ |  |
| Marketplace Moderator | 0 | ✓ | ✓ |  |  |  |

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
| `verification_status` | Verification Status | Select | Pending, Verified, Rejected |  |  | Pending | ✓ |  |  |
| `publication_status` | Publication Status | Select | Draft, Published, Unpublished |  |  | Draft | ✓ |  |  |
| `published_at` | Published At | Datetime |  |  |  |  |  | ✓ |  |

**Permissions**

| Role | Level | Read | Write | Create | Delete | If owner |
|---|---|---|---|---|---|---|
| System Manager | 0 | ✓ | ✓ | ✓ | ✓ |  |
| Marketplace Moderator | 0 | ✓ | ✓ | ✓ |  |  |
| Guest | 0 | ✓ |  |  |  |  |
| System Manager | 1 | ✓ | ✓ |  |  |  |
| Marketplace Moderator | 1 | ✓ | ✓ |  |  |  |
| Invoicing Owner | 0 | ✓ | ✓ | ✓ |  |  |

## Marketplace Project

A freelance project posted by a client, shown by card-project.php, project-detail.php, and the projects.php catalog. 'proposals_count' was already removed from the live UI in a prior pass (it is now derived by counting Marketplace Proposal rows, not stored).

- **Module:** `Marketplace`
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

**Permissions**

| Role | Level | Read | Write | Create | Delete | If owner |
|---|---|---|---|---|---|---|
| System Manager | 0 | ✓ | ✓ | ✓ | ✓ |  |
| Marketplace Moderator | 0 | ✓ | ✓ |  |  |  |
| Guest | 0 | ✓ |  |  |  |  |
| System Manager | 1 | ✓ | ✓ |  |  |  |
| Marketplace Moderator | 1 | ✓ | ✓ |  |  |  |
| Invoicing Owner | 0 | ✓ | ✓ | ✓ |  |  |

## Marketplace Proposal

ASSUMPTION / NOT YET IN THE WORDPRESS UI: project-detail.php's 'تقديم عرض على المشروع' button is an honest demo redirect to app.edariba with no proposal form on the public site today (data-edariba-demo-action). This DocType is still required because the product brief explicitly states freelancers submit proposals to projects (Mostaql-style) as one of the three core offerings, and app.edariba (not WordPress) is where that authenticated flow lives. Field set below is the minimum any such flow needs; confirm against the actual app.edariba form before building UI on top of it. Fully private: no Guest access anywhere.

- **Module:** `Marketplace`
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
| Marketplace Moderator | 0 | ✓ | ✓ |  |  |  |
| Guest | 0 | ✓ |  |  |  |  |
| Invoicing Owner | 0 | ✓ | ✓ | ✓ | ✓ |  |

## Marketplace Tag

Generic free-text label row, reused as the child table behind Marketplace Profile.specialties, Marketplace Service.badges, Marketplace Service.features, and Marketplace Project.required_skills. These are rendered as plain tag chips in the current WordPress templates (array_slice($acc['specialties'],0,4) etc.) with no controlled vocabulary or cross-entity lookup today, so one reusable free-text child doctype is correct instead of four near-identical ones or a premature taxonomy Link.

- **Module:** `Marketplace`
- **Child table:** `Yes`

| Fieldname | Label | Type | Options | Required | Unique | Default | In list | Read only | Level |
|---|---|---|---|---|---|---|---|---|---|
| `label` | Label | Data |  | ✓ |  |  | ✓ |  |  |
