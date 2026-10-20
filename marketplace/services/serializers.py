"""Public field allowlists. The one place that decides what a Guest is ever
allowed to see for each Marketplace DocType — never return doc.as_dict()
or frappe.get_all(..., fields=["*"]) for a public response.

bio/description live in *_LIST_FIELDS, not a "detail-only" split, because
every list-view card in the real WordPress templates renders a truncated
version unconditionally (card-accountant.php's bio, card-service.php's and
card-project.php's description, all with `line-clamp-2`/`-3` CSS, not a PHP
null-check) — leaving them out of a list response doesn't just hide text,
it throws a TypeError in esc_html() on a missing array key. Only genuinely
separate child-table data (qualifications, badges, features, required_skills)
and the two case-study fields are true detail-only additions."""

from marketplace.services.partner import is_partner

PROFILE_LIST_FIELDS = [
	"name",
	"display_name",
	"slug",
	"headline",
	"profile_type",
	"governorate",
	"area",
	"experience_years",
	"avatar",
	"bio",
	"offers_services",
	"accepts_projects",
]
PROFILE_DETAIL_EXTRA_FIELDS = ["case_study_title", "case_study_text"]

SERVICE_LIST_FIELDS = [
	"name",
	"title",
	"slug",
	"provider",
	"category",
	"price",
	"currency",
	"price_unit",
	"thumbnail",
	"description",
]
SERVICE_DETAIL_EXTRA_FIELDS: list[str] = []

PROJECT_LIST_FIELDS = [
	"name",
	"title",
	"slug",
	"category",
	"client_display_name",
	"client_type",
	"budget_min",
	"budget_max",
	"currency",
	"deadline",
	"escrow",
	"published_at",
	"description",
]
PROJECT_DETAIL_EXTRA_FIELDS: list[str] = []


def serialize_profile(doc, detail: bool = False) -> dict:
	fields = PROFILE_LIST_FIELDS + (PROFILE_DETAIL_EXTRA_FIELDS if detail else [])
	out = {f: doc.get(f) for f in fields}
	# Computed from the owner, who is never exposed (doc.user is not a public field).
	out["is_partner"] = is_partner(doc.user)
	out["specialties"] = [row.label for row in doc.specialties]
	if detail:
		out["qualifications"] = [
			{"title": r.title, "issuer": r.issuer, "year": r.year} for r in doc.qualifications
		]
	return out


def serialize_service(doc, detail: bool = False) -> dict:
	fields = SERVICE_LIST_FIELDS + (SERVICE_DETAIL_EXTRA_FIELDS if detail else [])
	out = {f: doc.get(f) for f in fields}
	out["badges"] = [row.label for row in doc.badges]
	out["features"] = [row.label for row in doc.features]
	return out


def serialize_project(doc, detail: bool = False) -> dict:
	fields = PROJECT_LIST_FIELDS + (PROJECT_DETAIL_EXTRA_FIELDS if detail else [])
	out = {f: doc.get(f) for f in fields}
	out["required_skills"] = [row.label for row in doc.required_skills]
	return out
