"""Published URL, kept stable: /api/method/marketplace.api.public.accountants.<fn>.

The endpoints live in marketplace/public_api/accountants.py; this module only re-exports them
(Frappe resolves the dotted path to the same whitelisted function).
"""

from marketplace.marketplace.public_api.accountants import get_accountant, list_accountants  # noqa: F401
