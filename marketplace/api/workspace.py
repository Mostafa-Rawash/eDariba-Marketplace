"""Published URL, kept stable: /api/method/marketplace.api.workspace.<fn>.

The endpoints live in inquiries/api.py; this module only re-exports them
(Frappe resolves the dotted path to the same whitelisted function).
"""

from marketplace.inquiries.api import (  # noqa: F401
	get_request,
	list_requests,
	respond_request,
	set_request_status,
	submit_request,
	support_set_request_status,
	sync_profile_link,
)
