"""Profile verification policy, in one place.

TEMPORARY (decided 2026-10-26): nobody reviews accounts, so verification is
bypassed. Every profile is Verified by default and owners never have to ask
for, or wait for, approval. Services have no verification field of their own:
a published service is only as verified as its provider's profile.

What "bypassed" means here:
- a new profile is created Verified (verification_method = "Automatic"),
  whatever the client sent;
- a Pending profile becomes Verified the next time it is saved, and the patch
  marketplace.patches.verify_profiles_by_default does this once for existing
  rows;
- only a System Manager may change verification_status by hand, e.g. to
  Rejected (shared/permissions.py can_edit_any); owners and the support team
  (Marketplace Moderator) cannot, through any API. A verifier role is planned
  for when verification comes back.

To restore a real verification workflow:
1. set "marketplace_verification_required": 1 in site_config.json (or flip
   the default below);
2. optionally move every Automatic verification back to Pending:
   UPDATE `tabMarketplace Profile` SET verification_status='Pending',
   verification_method=NULL, verified_at=NULL
   WHERE verification_method='Automatic';
3. add the verifier role to shared/permissions.py (can_edit_any is System
   Manager only today), build its review screen, bind badges to Verified only.
Nothing else in the code base assumes verification is off.

Pure Python apart from reading site config, so the rules are unit-tested.
"""

PENDING = "Pending"
VERIFIED = "Verified"
REJECTED = "Rejected"

AUTOMATIC = "Automatic"
MODERATOR = "Moderator"

# The default when site_config says nothing.
VERIFICATION_REQUIRED_DEFAULT = False


def verification_required(conf: dict | None = None) -> bool:
	if conf is None:
		import frappe

		conf = frappe.local.conf or {}
	return bool(conf.get("marketplace_verification_required", VERIFICATION_REQUIRED_DEFAULT))


def status_for_new_profile(required: bool) -> tuple[str, str | None]:
	"""(verification_status, verification_method) a new profile starts with."""
	return (PENDING, None) if required else (VERIFIED, AUTOMATIC)


def auto_verify(current: str | None, required: bool) -> bool:
	"""True when a saved profile in `current` should become Verified now.
	Rejected is a moderator decision and is never undone automatically."""
	return not required and current in (None, "", PENDING)


def owner_may_change(previous: str | None, new: str | None, required: bool) -> bool:
	"""Whether a non-moderator owner may move verification_status from
	`previous` to `new`. Only one change is open to owners, and only while
	verification is required: sending a Rejected profile back for review."""
	if previous == new:
		return True
	return required and (previous, new) == (REJECTED, PENDING)
