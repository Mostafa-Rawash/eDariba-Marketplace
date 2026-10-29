"""Rules shared by the support endpoints (inquiries/api.py and freelance/api.py).

Pure Python, unit-tested through inquiries/tests/test_request_rules.py.
"""

# A support change must say why; the note is shown to both parties.
SUPPORT_REASON_MIN = 10
SUPPORT_REASON_MAX = 500


def support_reason_ok(reason: str | None) -> bool:
	return SUPPORT_REASON_MIN <= len((reason or "").strip()) <= SUPPORT_REASON_MAX
