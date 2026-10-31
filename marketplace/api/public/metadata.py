"""Published URL, kept stable: /api/method/marketplace.api.public.metadata.<fn>.

The endpoints live in marketplace/public_api/metadata.py; this module only re-exports them
(Frappe resolves the dotted path to the same whitelisted function).
"""

from marketplace.marketplace.public_api.metadata import get_metadata  # noqa: F401
