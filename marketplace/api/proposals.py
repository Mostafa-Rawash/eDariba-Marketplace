"""Published URL, kept stable: /api/method/marketplace.api.proposals.<fn>.

The endpoints live in freelance/api.py; this module only re-exports them
(Frappe resolves the dotted path to the same whitelisted function).
"""

from marketplace.freelance.api import set_proposal_status, support_close_project, withdraw_proposal  # noqa: F401
