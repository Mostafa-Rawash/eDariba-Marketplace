"""Published URL, kept stable: /api/method/marketplace.api.gamification.<fn>.

The endpoints live in gamification/api.py; this module only re-exports them
(Frappe resolves the dotted path to the same whitelisted function).
"""

from marketplace.gamification.api import my_achievements, my_points  # noqa: F401
