"""Rules for the provider self-service endpoints (api/provider.py).

Pure Python, no Frappe import, so the rules are unit-tested on their own
(services/tests/test_provider_rules.py), like request_rules.py.

Covers which fields an owner may write on their profile and services, how
tag lists are cleaned, how slugs are derived, which images are accepted, and
the proposal status rules for freelancers and project owners.
"""

import base64
import re

# ---------------------------------------------------------------- Profile ---

# Fields a profile owner may set. Everything else (user, slug,
# verification_status, publication_status, published_at) is decided by the
# endpoint or by a moderator.
PROFILE_EDITABLE_FIELDS = (
	"profile_type",
	"display_name",
	"headline",
	"governorate",
	"area",
	"experience_years",
	"bio",
	"case_study_title",
	"case_study_text",
	"offers_services",
	"accepts_projects",
)
PROFILE_TYPES = ("Individual", "Firm")
MAX_SPECIALTIES = 12
MAX_QUALIFICATIONS = 10

# --------------------------------------------------------------- Services ---

SERVICE_EDITABLE_FIELDS = ("title", "category", "price", "price_unit", "description")
PRICE_UNITS = ("Total", "Monthly", "Per Session")
SERVICE_STATUSES = ("Draft", "Published", "Unpublished")
MAX_FEATURES = 8
MAX_BADGES = 3

# ------------------------------------------------------------------ Tags ---

TAG_MAX_LENGTH = 140


def clean_tags(values, limit: int) -> list[str]:
	"""Trimmed, de-duplicated (order kept) labels, at most `limit` of them.
	Accepts a list of strings or of {"label": ...} rows."""
	out: list[str] = []
	for value in values or []:
		label = value.get("label") if isinstance(value, dict) else value
		label = str(label or "").strip()[:TAG_MAX_LENGTH]
		if label and label not in out:
			out.append(label)
		if len(out) >= limit:
			break
	return out


def clean_qualifications(rows) -> list[dict]:
	"""Rows with a title and an issuer; year kept as text (the field is Data)."""
	out = []
	for row in rows or []:
		if not isinstance(row, dict):
			continue
		title = str(row.get("title") or "").strip()[:TAG_MAX_LENGTH]
		issuer = str(row.get("issuer") or "").strip()[:TAG_MAX_LENGTH]
		year = str(row.get("year") or "").strip()[:4]
		if title and issuer:
			out.append({"title": title, "issuer": issuer, "year": year if year.isdigit() else ""})
		if len(out) >= MAX_QUALIFICATIONS:
			break
	return out


# ----------------------------------------------------------------- Slugs ---

_SLUG_CHARS = re.compile(r"[^a-z0-9]+")


def slug_base(text: str, fallback: str = "accountant") -> str:
	"""Latin slug from free text: lower case, a-z0-9 and hyphens, at most 40
	characters. Arabic or other scripts produce nothing, so `fallback` is used.
	For a profile, pass the local part of the owner's email."""
	slug = _SLUG_CHARS.sub("-", (text or "").lower()).strip("-")[:40].strip("-")
	return slug or fallback


def unique_slug(base: str, taken) -> str:
	"""`base`, or `base-2`, `base-3`… — the first one `taken(slug)` says is free."""
	if not taken(base):
		return base
	n = 2
	while taken(f"{base}-{n}"):
		n += 1
	return f"{base}-{n}"


# ---------------------------------------------------------------- Images ---

IMAGE_TYPES = {"image/png": "png", "image/jpeg": "jpg"}
IMAGE_MAX_BYTES = 2 * 1024 * 1024
_DATA_URL = re.compile(r"^data:(image/[a-z+]+);base64,([A-Za-z0-9+/=\s]+)$")


class ImageError(ValueError):
	pass


def decode_image(data_url: str) -> tuple[str, bytes]:
	"""(extension, bytes) for a PNG or JPEG data URL of at most 2 MB.
	Checks the file signature, not only the declared type."""
	match = _DATA_URL.match(data_url or "")
	if not match:
		raise ImageError("Send the image as a PNG or JPEG data URL.")
	mime, payload = match.group(1), match.group(2)
	if mime not in IMAGE_TYPES:
		raise ImageError("The image must be PNG or JPEG.")
	# Reject before decoding a huge payload: base64 is 4/3 of the bytes.
	if len(payload) > IMAGE_MAX_BYTES * 4 // 3 + 8:
		raise ImageError("The image must be 2 MB or smaller.")
	try:
		content = base64.b64decode(payload, validate=False)
	except (ValueError, TypeError) as exc:
		raise ImageError("The image could not be read.") from exc
	if len(content) > IMAGE_MAX_BYTES:
		raise ImageError("The image must be 2 MB or smaller.")
	is_png = content.startswith(b"\x89PNG\r\n\x1a\n")
	is_jpeg = content.startswith(b"\xff\xd8\xff")
	if not (is_png or is_jpeg):
		raise ImageError("The image must be PNG or JPEG.")
	return ("png" if is_png else "jpg"), content


# ------------------------------------------------------------- Proposals ---

PROPOSAL_STATUSES = ("Submitted", "Shortlisted", "Accepted", "Rejected", "Withdrawn")
ACTIVE_PROPOSAL_STATUSES = ("Submitted", "Shortlisted")

# What the project owner may move a proposal to. "Submitted" from
# Shortlisted means "remove from the shortlist".
_OWNER_TRANSITIONS = {
	"Submitted": ("Shortlisted", "Accepted", "Rejected"),
	"Shortlisted": ("Submitted", "Accepted", "Rejected"),
}


def owner_next_statuses(current: str) -> tuple[str, ...]:
	return _OWNER_TRANSITIONS.get(current, ())


def owner_can_set(current: str, new: str) -> bool:
	return new in owner_next_statuses(current)


def freelancer_can_withdraw(current: str) -> bool:
	return current in ACTIVE_PROPOSAL_STATUSES


COVER_LETTER_MIN = 80
COVER_LETTER_MAX = 2000
