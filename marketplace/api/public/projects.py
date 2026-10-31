"""Published URL, kept stable: /api/method/marketplace.api.public.projects.<fn>.

The endpoints live in freelance/public_api.py; this module only re-exports them
(Frappe resolves the dotted path to the same whitelisted function).
"""

from marketplace.freelance.public_api import get_project, list_projects  # noqa: F401
