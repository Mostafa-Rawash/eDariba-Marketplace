"""Profile completeness, computed on the server: the single definition used by
the stats endpoints, gamification and the publish gate. The app's
«اكتمال الملف» checklist (pre-edariba MyProfile.vue `completion`) shows the
same five items; it should read `completion` from the API rather than keep
its own copy.

Pure Python: takes a plain dict (a profile's fields, child tables as lists),
so the rules are unit-tested without a site.
"""

import re

BIO_MIN_CHARS = 80
MIN_SPECIALTIES = 3
MAX_EXPERIENCE_YEARS = 70

# key -> Arabic label shown in the app
ITEMS = (
	("basics", "البيانات الأساسية والصورة الشخصية"),
	("bio_experience", "النبذة المهنية وتاريخ الخبرة"),
	("specialties", "التخصصات الدقيقة (٣ على الأقل)"),
	("qualifications", "المؤهلات والتراخيص"),
	("case_study", "دراسة حالة أو إنجاز"),
)

_TAGS = re.compile(r"<[^>]+>")


def plain_text(value) -> str:
	"""Text Editor HTML to the visible text, whitespace collapsed."""
	text = _TAGS.sub(" ", str(value or "")).replace("&nbsp;", " ")
	return " ".join(text.split())


def _filled(value) -> bool:
	return bool(str(value or "").strip())


def _experience(value) -> int | None:
	try:
		years = int(value)
	except (TypeError, ValueError):
		return None
	return years if 0 <= years <= MAX_EXPERIENCE_YEARS else None


def _labels(rows, key: str) -> list[str]:
	out = []
	for row in rows or []:
		value = row.get(key) if isinstance(row, dict) else row
		if _filled(value):
			out.append(str(value).strip())
	return out


def item_states(profile: dict) -> dict[str, bool]:
	years = _experience(profile.get("experience_years"))
	return {
		"basics": all(_filled(profile.get(f)) for f in ("display_name", "headline", "governorate", "avatar")),
		"bio_experience": len(plain_text(profile.get("bio"))) >= BIO_MIN_CHARS and bool(years),
		"specialties": len(set(_labels(profile.get("specialties"), "label"))) >= MIN_SPECIALTIES,
		"qualifications": bool(_labels(profile.get("qualifications"), "title")),
		"case_study": _filled(profile.get("case_study_title")),
	}


def completion(profile: dict) -> dict:
	"""{"percent": 0-100, "complete": bool, "items": [{key, label, done}]}"""
	states = item_states(profile)
	items = [{"key": key, "label": label, "done": states[key]} for key, label in ITEMS]
	done = sum(1 for i in items if i["done"])
	return {"percent": round(done * 100 / len(items)), "complete": done == len(items), "items": items}


def publish_problems(profile: dict) -> list[str]:
	"""What a profile is missing before it may be published. Kept to the
	existing rule (bio, headline, years of experience present), not the full
	checklist, so publishing is not made stricter by this module."""
	missing = []
	if not plain_text(profile.get("bio")):
		missing.append("bio")
	if not _filled(profile.get("headline")):
		missing.append("headline")
	if profile.get("experience_years") in (None, ""):
		missing.append("experience_years")
	return missing


def profile_dict(doc) -> dict:
	"""A Marketplace Profile document (or dict) as the plain dict above."""
	get = doc.get
	return {
		"display_name": get("display_name"),
		"headline": get("headline"),
		"governorate": get("governorate"),
		"avatar": get("avatar"),
		"bio": get("bio"),
		"experience_years": get("experience_years"),
		"specialties": [{"label": r.get("label")} for r in (get("specialties") or [])],
		"qualifications": [{"title": r.get("title")} for r in (get("qualifications") or [])],
		"case_study_title": get("case_study_title"),
	}


def for_doc(doc) -> dict:
	return completion(profile_dict(doc))
