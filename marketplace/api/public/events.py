"""Published URL, kept stable: /api/method/marketplace.api.public.events.<fn>.

The endpoints live in activity/public_api.py; this module only re-exports them
(Frappe resolves the dotted path to the same whitelisted function).
"""

from marketplace.activity.public_api import track  # noqa: F401
