"""Published URL, kept stable: /api/method/marketplace.api.public.services.<fn>.

The endpoints live in marketplace/public_api/services.py; this module only re-exports them
(Frappe resolves the dotted path to the same whitelisted function).
"""

from marketplace.marketplace.public_api.services import get_service, list_services  # noqa: F401
