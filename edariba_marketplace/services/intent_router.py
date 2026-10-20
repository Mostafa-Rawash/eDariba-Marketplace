"""Deterministic keyword -> entity_type classification for search.search(auto_intent=1)
(the former Chat discovery endpoint). This is NOT an LLM — no external calls, fully testable.

Ported 1:1 from the existing WordPress Chat_Router
(plugins/edariba-marketplace/includes/class-chat-router.php) rather than
re-deriving a second keyword list that could drift from it. If the keyword
lists ever change, change both, or retire the PHP version in favor of
calling this endpoint — see Remaining Questions in the final report.
"""

PROJECT_KEYWORDS = ["مشروع", "مناقصة", "فريلانس", "مستقل", "اطرح", "عرض سعر", "أبحث عن محاسب لـ"]
SERVICE_KEYWORDS = ["باقة", "خدمة جاهزة", "سعر", "كام", "تكلفة", "اشتراك", "إقرار", "الفاتورة", "تأسيس", "مسك دفاتر", "دراسة جدوى", "قيمة مضافة", "vat"]
ACCOUNTANT_KEYWORDS = ["محاسب", "مكتب", "مراجع", "خبير", "استشار", "فاحص", "قانوني"]

CATEGORY_KEYWORDS = {
	"bookkeeping": ["مسك دفاتر", "دفاتر", "مرتبات", "ميزان"],
	"tax": ["ضريبة", "ضرائب", "قيمة مضافة", "vat", "فحص", "طعن", "إقرار", "منازعة"],
	"financial-statements": ["قوائم مالية", "ميزانية", "مراجعة", "تدقيق", "مراقب حسابات"],
	"company-formation": ["تأسيس", "سجل تجاري", "ترخيص", "شركة ذات مسؤولية"],
	"feasibility": ["جدوى", "تمويل", "دراسة", "استثمار"],
	"e-invoice": ["فاتورة", "إيصال", "إلكترون", "eta", "ربط", "egs"],
}


def _has_any(haystack: str, needles: list[str]) -> bool:
	return any(n and n.lower() in haystack for n in needles)


def guess_category(query_lower: str) -> str:
	for slug, keywords in CATEGORY_KEYWORDS.items():
		if _has_any(query_lower, keywords):
			return slug
	return ""


def classify(query: str) -> dict:
	"""Returns {"entity_type": str, "matched": bool, "category": str}."""
	q = (query or "").lower()
	category = guess_category(q)

	if _has_any(q, PROJECT_KEYWORDS):
		return {"entity_type": "project", "matched": True, "category": category}
	if _has_any(q, SERVICE_KEYWORDS):
		return {"entity_type": "service", "matched": True, "category": category}
	if _has_any(q, ACCOUNTANT_KEYWORDS):
		return {"entity_type": "accountant", "matched": True, "category": category}

	return {"entity_type": "accountant", "matched": False, "category": category}
