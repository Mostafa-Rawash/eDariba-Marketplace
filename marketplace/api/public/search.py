"""Published URL, kept stable: /api/method/marketplace.api.public.search.<fn>.

The endpoints live in search/public_api.py; this module only re-exports them
(Frappe resolves the dotted path to the same whitelisted function).
"""

from marketplace.search.public_api import search  # noqa: F401
