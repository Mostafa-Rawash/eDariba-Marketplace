"""Logged-in provider self-service for the app (app.edariba.com).

Routes (POST unless noted, session cookie through the SPA's /logic proxy):
  marketplace.api.provider.get_my_profile                (GET)
  marketplace.api.provider.save_my_profile
  marketplace.api.provider.resubmit_profile
  marketplace.api.provider.list_my_services              (GET)
  marketplace.api.provider.save_my_service
  marketplace.api.provider.set_service_status
  marketplace.api.provider.delete_my_service
  marketplace.api.provider.submit_proposal
  marketplace.api.provider.list_my_proposals             (GET)
  marketplace.api.provider.withdraw_proposal
  marketplace.api.provider.list_project_proposals        (GET)
  marketplace.api.provider.set_proposal_status

Same rules as api/workspace.py: every function is @frappe.whitelist() without
allow_guest; the user always comes from frappe.session.user and is never
accepted as a parameter; ownership is re-checked on every call; a record that
is not yours answers "not found", exactly like a missing one; only allowlisted
fields are written (services/provider_rules.py). Saves use
ignore_permissions=True because these checks replace the DocPerm check
(normal users have none), while the DocType controllers still enforce their
invariants: only moderators verify, only verified profiles publish, one
active proposal per project, no proposal on your own project.

Shapes are documented, with sample records, in the app repo:
pre-edariba/src/marketplace/DUMMY_DATA.md.
"""

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, flt, now_datetime, strip_html

from marketplace.api.common import ok
from marketplace.services import provider_rules as rules
from marketplace.services.uploads import resolve_image

# Per user, counted from the proposals table, like REQUEST_LIMIT_PER_HOUR.
PROPOSAL_LIMIT_PER_HOUR = 20


def _user() -> str:
	return frappe.session.user


def _parse(value) -> dict:
	value = frappe.parse_json(value) if isinstance(value, str) else value
	if not isinstance(value, dict):
		frappe.throw(_("Send the data as an object."))
	return value


def _not_found(what: str):
	frappe.throw(_("{0} not found.").format(what), frappe.DoesNotExistError)


def _my_profile_name(user: str) -> str | None:
	return frappe.db.get_value("Marketplace Profile", {"user": user}, "name")


def _require_my_profile():
	name = _my_profile_name(_user())
	if not name:
		_not_found(_("Profile"))
	return frappe.get_doc("Marketplace Profile", name)


def _plain(html: str | None) -> str:
	"""Text Editor fields are stored as HTML; the app edits plain text."""
	return strip_html(html or "").strip()


# ---------------------------------------------------------------- Profile ---


def _serialize_my_profile(doc) -> dict:
	return {
		"name": doc.name,
		"slug": doc.slug,
		"profile_type": doc.profile_type,
		"display_name": doc.display_name,
		"headline": doc.headline,
		"governorate": doc.governorate,
		"area": doc.area,
		"experience_years": doc.experience_years,
		"avatar": doc.avatar,
		"bio": _plain(doc.bio),
		"specialties": [row.label for row in doc.specialties],
		"qualifications": [{"title": r.title, "issuer": r.issuer, "year": r.year} for r in doc.qualifications],
		"case_study_title": doc.case_study_title,
		"case_study_text": doc.case_study_text,
		"offers_services": bool(doc.offers_services),
		"accepts_projects": bool(doc.accepts_projects),
		"verification_status": doc.verification_status,
		"publication_status": doc.publication_status,
		"published": doc.publication_status == "Published",
		# No field stores a reason yet; moderators explain by email for now.
		"rejection_reason": "",
	}


@frappe.whitelist()
def get_my_profile():
	return ok(_serialize_my_profile(_require_my_profile()))


@frappe.whitelist(methods=["POST"])
def save_my_profile(profile):
	"""Create the caller's profile (an application to be listed: Pending,
	Draft) or update it. `published` toggles the listing once Verified."""
	data = _parse(profile)
	user = _user()
	name = _my_profile_name(user)

	if name:
		doc = frappe.get_doc("Marketplace Profile", name)
	else:
		email = frappe.db.get_value("User", user, "email") or user
		base = rules.slug_base(email.split("@")[0])
		doc = frappe.new_doc("Marketplace Profile")
		doc.user = user
		doc.slug = rules.unique_slug(base, lambda s: frappe.db.exists("Marketplace Profile", {"slug": s}))
		doc.verification_status = "Pending"
		doc.publication_status = "Draft"

	for field in rules.PROFILE_EDITABLE_FIELDS:
		if field in data:
			doc.set(field, data[field])
	if doc.profile_type not in rules.PROFILE_TYPES:
		frappe.throw(_("Choose a profile type."))
	if "experience_years" in data:
		doc.experience_years = max(0, min(cint(data["experience_years"]), 60))
	for flag in ("offers_services", "accepts_projects"):
		if flag in data:
			doc.set(flag, 1 if data[flag] else 0)

	if "specialties" in data:
		doc.set("specialties", [{"label": t} for t in rules.clean_tags(data["specialties"], rules.MAX_SPECIALTIES)])
	if "qualifications" in data:
		doc.set("qualifications", rules.clean_qualifications(data["qualifications"]))
	if "avatar" in data:
		doc.avatar = resolve_image(data["avatar"], doc.avatar, _("profile photo"))

	# Publishing is the owner's choice, but only once Verified (the controller
	# refuses otherwise with a clear message).
	if "published" in data and not doc.is_new():
		if (doc.publication_status == "Published") != bool(data["published"]):
			doc.publication_status = "Published" if data["published"] else "Unpublished"

	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)
	return ok(_serialize_my_profile(doc))


@frappe.whitelist(methods=["POST"])
def resubmit_profile():
	"""Send a Rejected profile back to the moderators (Rejected → Pending).
	The profile controller allows exactly this change from the owner."""
	doc = _require_my_profile()
	if doc.verification_status != "Rejected":
		frappe.throw(_("Only a rejected profile can be sent for review again."))
	doc.verification_status = "Pending"
	doc.save(ignore_permissions=True)
	return ok(_serialize_my_profile(doc))


# ---------------------------------------------------------------- Services ---


def _category_titles(slugs) -> dict:
	slugs = [s for s in set(slugs) if s]
	if not slugs:
		return {}
	return dict(
		frappe.get_all(
			"Marketplace Category",
			filters={"name": ["in", slugs]},
			fields=["name", "title"],
			as_list=True,
			ignore_permissions=True,
		)
	)


def _serialize_my_service(doc, titles: dict | None = None) -> dict:
	titles = titles if titles is not None else _category_titles([doc.category])
	return {
		"name": doc.name,
		"slug": doc.slug,
		"title": doc.title,
		"category": doc.category,
		"category_title": titles.get(doc.category) or doc.category,
		"price": doc.price,
		"currency": doc.currency,
		"price_unit": doc.price_unit,
		"thumbnail": doc.thumbnail,
		"description": _plain(doc.description),
		"features": [row.label for row in doc.features],
		"badges": [row.label for row in doc.badges],
		"status": doc.publication_status,
	}


def _load_my_service(name: str, profile_name: str):
	if not name or frappe.db.get_value("Marketplace Service", name, "provider") != profile_name:
		_not_found(_("Service"))
	return frappe.get_doc("Marketplace Service", name)


@frappe.whitelist()
def list_my_services():
	profile = _require_my_profile()
	names = frappe.get_all(
		"Marketplace Service",
		filters={"provider": profile.name},
		order_by="creation desc",
		pluck="name",
		ignore_permissions=True,
	)
	docs = [frappe.get_doc("Marketplace Service", n) for n in names]
	titles = _category_titles([d.category for d in docs])
	return ok([_serialize_my_service(d, titles) for d in docs])


@frappe.whitelist(methods=["POST"])
def save_my_service(service):
	"""Create (no `name`) or update one of the caller's services. `status`
	Draft saves incomplete work; Published needs every required field."""
	data = _parse(service)
	profile = _require_my_profile()
	status = data.get("status") or "Draft"
	if status not in rules.SERVICE_STATUSES:
		frappe.throw(_("Unknown status."))

	if data.get("name"):
		doc = _load_my_service(data["name"], profile.name)
	else:
		doc = frappe.new_doc("Marketplace Service")
		doc.provider = profile.name
		base = f"{profile.slug}-{rules.slug_base(data.get('title') or '', 'service')}"
		doc.slug = rules.unique_slug(base, lambda s: frappe.db.exists("Marketplace Service", {"slug": s}))

	for field in rules.SERVICE_EDITABLE_FIELDS:
		if field in data:
			doc.set(field, data[field])
	doc.title = (doc.title or "").strip()
	if not doc.title:
		frappe.throw(_("Write a title for the service."))
	if "price" in data:
		doc.price = max(0, flt(data["price"]))
	if doc.price_unit not in rules.PRICE_UNITS:
		doc.price_unit = "Total"
	if doc.category and not frappe.db.exists("Marketplace Category", {"name": doc.category, "is_active": 1}):
		frappe.throw(_("Choose a category from the list."))
	if "features" in data:
		doc.set("features", [{"label": t} for t in rules.clean_tags(data["features"], rules.MAX_FEATURES)])
	if "badges" in data:
		doc.set("badges", [{"label": t} for t in rules.clean_tags(data["badges"], rules.MAX_BADGES)])
	if "thumbnail" in data:
		doc.thumbnail = resolve_image(data["thumbnail"], doc.thumbnail, _("service image"))

	doc.publication_status = status
	if status == "Published" and not (flt(doc.price) > 0):
		frappe.throw(_("Set a price above zero before publishing."))
	# A draft may be incomplete; publishing runs the full mandatory check.
	doc.flags.ignore_mandatory = status == "Draft"
	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)
	return ok(_serialize_my_service(doc))


@frappe.whitelist(methods=["POST"])
def set_service_status(name: str, status: str):
	if status not in ("Published", "Unpublished"):
		frappe.throw(_("Unknown status."))
	profile = _require_my_profile()
	doc = _load_my_service(name, profile.name)
	doc.publication_status = status
	doc.save(ignore_permissions=True)
	return ok(_serialize_my_service(doc))


@frappe.whitelist(methods=["POST"])
def delete_my_service(name: str):
	profile = _require_my_profile()
	doc = _load_my_service(name, profile.name)
	if frappe.db.exists("Marketplace Inquiry", {"related_service": doc.name}):
		frappe.throw(_("Requests refer to this service. Unpublish it instead of deleting it."))
	frappe.delete_doc("Marketplace Service", doc.name, ignore_permissions=True)
	return ok(None)


# --------------------------------------------------------------- Proposals ---


def _project_summary(name: str) -> dict:
	row = frappe.db.get_value(
		"Marketplace Project",
		name,
		["name", "slug", "title", "client_display_name", "budget_min", "budget_max", "currency", "publication_status"],
		as_dict=True,
	)
	return dict(row or {})


def _serialize_my_proposal(doc, project: dict | None = None) -> dict:
	project = project or _project_summary(doc.project)
	return {
		"name": doc.name,
		"project": {"slug": project.get("slug") or doc.project, "title": project.get("title")},
		"client_display_name": project.get("client_display_name"),
		"amount": doc.proposed_amount,
		"currency": doc.currency,
		"duration_days": doc.estimated_days,
		"cover_letter": _plain(doc.cover_letter),
		"status": doc.status,
		"submitted_at": doc.submitted_at,
	}


@frappe.whitelist(methods=["POST"])
def submit_proposal(project: str, amount, duration_days, cover_letter: str):
	user = _user()
	profile = frappe.db.get_value(
		"Marketplace Profile",
		{"user": user},
		["name", "verification_status", "accepts_projects"],
		as_dict=True,
	)
	if not profile or profile.verification_status != "Verified":
		frappe.throw(_("You need a verified professional profile to send proposals."))
	if not profile.accepts_projects:
		frappe.throw(_("Turn on 'Accepts Projects' on your profile before sending proposals."))

	if frappe.db.get_value("Marketplace Project", project, "publication_status") != "Published":
		frappe.throw(_("This project is not open for proposals."))

	amount = flt(amount)
	days = cint(duration_days)
	letter = (cover_letter or "").strip()
	if amount <= 0:
		frappe.throw(_("Enter the proposal amount."))
	if days < 1:
		frappe.throw(_("Enter the duration in days."))
	if not (rules.COVER_LETTER_MIN <= len(letter) <= rules.COVER_LETTER_MAX):
		frappe.throw(
			_("The cover letter must be {0} to {1} characters.").format(rules.COVER_LETTER_MIN, rules.COVER_LETTER_MAX)
		)

	recent = frappe.db.count(
		"Marketplace Proposal",
		{"submitted_by": user, "creation": [">", add_to_date(now_datetime(), hours=-1)]},
	)
	if recent >= PROPOSAL_LIMIT_PER_HOUR:
		frappe.throw(_("You have sent too many proposals. Please try again later."), frappe.RateLimitExceededError)

	doc = frappe.get_doc(
		{
			"doctype": "Marketplace Proposal",
			"project": project,
			"freelancer": profile.name,
			"proposed_amount": amount,
			"estimated_days": days,
			"cover_letter": letter,
		}
	)
	doc.insert(ignore_permissions=True)
	return ok(_serialize_my_proposal(doc))


@frappe.whitelist()
def list_my_proposals():
	names = frappe.get_all(
		"Marketplace Proposal",
		filters={"submitted_by": _user()},
		order_by="creation desc",
		pluck="name",
		limit_page_length=200,
		ignore_permissions=True,
	)
	docs = [frappe.get_doc("Marketplace Proposal", n) for n in names]
	projects = {p: _project_summary(p) for p in {d.project for d in docs}}
	return ok([_serialize_my_proposal(d, projects[d.project]) for d in docs])


@frappe.whitelist(methods=["POST"])
def withdraw_proposal(name: str):
	if not name or frappe.db.get_value("Marketplace Proposal", name, "submitted_by") != _user():
		_not_found(_("Proposal"))
	doc = frappe.get_doc("Marketplace Proposal", name)
	if not rules.freelancer_can_withdraw(doc.status):
		frappe.throw(_("Only an active proposal can be withdrawn."), frappe.PermissionError)
	doc.status = "Withdrawn"
	doc.save(ignore_permissions=True)
	return ok(_serialize_my_proposal(doc))


def _load_my_project(project: str) -> dict:
	"""The caller's project, in any status (a closed project still shows its
	proposals). Not yours = not found."""
	if not project or frappe.db.get_value("Marketplace Project", project, "client") != _user():
		_not_found(_("Project"))
	return _project_summary(project)


def _serialize_received(doc, freelancers: dict) -> dict:
	f = freelancers.get(doc.freelancer) or {}
	return {
		"name": doc.name,
		"freelancer": {
			"slug": f.get("slug") or doc.freelancer,
			"display_name": f.get("display_name"),
			"headline": f.get("headline"),
			"avatar": f.get("avatar"),
			"experience_years": f.get("experience_years"),
			"verified": f.get("verification_status") == "Verified",
		},
		"amount": doc.proposed_amount,
		"currency": doc.currency,
		"duration_days": doc.estimated_days,
		"cover_letter": _plain(doc.cover_letter),
		"status": doc.status,
		"submitted_at": doc.submitted_at,
		"next_statuses": list(rules.owner_next_statuses(doc.status)),
	}


def _freelancers(names) -> dict:
	names = [n for n in set(names) if n]
	if not names:
		return {}
	rows = frappe.get_all(
		"Marketplace Profile",
		filters={"name": ["in", names]},
		fields=["name", "slug", "display_name", "headline", "avatar", "experience_years", "verification_status"],
		ignore_permissions=True,
	)
	return {r.name: r for r in rows}


@frappe.whitelist()
def list_project_proposals(project: str):
	summary = _load_my_project(project)
	names = frappe.get_all(
		"Marketplace Proposal",
		filters={"project": project},
		order_by="creation desc",
		pluck="name",
		ignore_permissions=True,
	)
	docs = [frappe.get_doc("Marketplace Proposal", n) for n in names]
	freelancers = _freelancers([d.freelancer for d in docs])
	return ok([_serialize_received(d, freelancers) for d in docs], meta={"project": summary})


@frappe.whitelist(methods=["POST"])
def set_proposal_status(project: str, name: str, status: str):
	"""Project owner: shortlist, un-shortlist, accept or reject. Accepting
	rejects every other active proposal and closes the project."""
	_load_my_project(project)
	if not name or frappe.db.get_value("Marketplace Proposal", name, "project") != project:
		_not_found(_("Proposal"))
	doc = frappe.get_doc("Marketplace Proposal", name)
	if not rules.owner_can_set(doc.status, status):
		frappe.throw(_("This status change is not allowed."), frappe.PermissionError)

	doc.status = status
	doc.save(ignore_permissions=True)

	if status == "Accepted":
		others = frappe.get_all(
			"Marketplace Proposal",
			filters={
				"project": project,
				"name": ["!=", doc.name],
				"status": ["in", list(rules.ACTIVE_PROPOSAL_STATUSES)],
			},
			pluck="name",
			ignore_permissions=True,
		)
		for other in others:
			other_doc = frappe.get_doc("Marketplace Proposal", other)
			other_doc.status = "Rejected"
			other_doc.save(ignore_permissions=True)
		project_doc = frappe.get_doc("Marketplace Project", project)
		project_doc.publication_status = "Closed"
		project_doc.save(ignore_permissions=True)

	return ok(_serialize_received(doc, _freelancers([doc.freelancer])))
