"""Published URL, kept stable: /api/method/marketplace.api.stats.<fn>.

The endpoints live in stats/api.py; this module only re-exports them
(Frappe resolves the dotted path to the same whitelisted function).
"""

from marketplace.stats.api import admin_stats, profile_completion, provider_stats  # noqa: F401
