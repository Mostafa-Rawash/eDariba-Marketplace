from . import __version__ as app_version  # noqa: F401

app_name = "marketplace"
app_title = "eDariba Marketplace"
app_publisher = "eDariba"
app_description = "Accountant directory, services marketplace, and freelance project marketplace for eDariba."
app_email = "dev@edariba.com"
app_license = "proprietary"

# Domain modules (modules.txt). Each one owns its DocTypes, rules, services
# and API; this file is the only place they are wired together:
#   marketplace/   Marketplace: profiles, services, catalog (categories, tags...)
#   inquiries/     Inquiries: client -> accountant requests
#   freelance/     Freelance: projects and proposals
#   activity/      Activity: views, searches, clicks, daily metrics
#   gamification/  Gamification: points ledger and achievements
# and plain packages with no DocTypes: search/ (Qdrant), stats/ (read models),
# shared/ (envelope, filters, roles). api/ keeps the published URLs stable.
#
# The only role this app adds is "Marketplace Moderator", for the sales /
# customer-support team (2026-10-29). It reads every profile, service,
# project, proposal and request in Desk, and may end an abandoned request
# or project through the support_* endpoints, always with a reason. It
# cannot edit listings, take part in a request, or change verification:
# only "System Manager" changes records it does not own
# (shared/permissions.py can_edit_any). Verification is bypassed for now
# (marketplace/verification.py); a verifier role comes with that feature.
#
# There are deliberately no provider/client roles: what a user can do in the
# marketplace comes from their records (a Marketplace Profile they own, with its
# offers_services / accepts_projects switches; requests they sent). The app's
# users hold the accounting "Invoicing Owner" role, which has DocPerms on
# Profile, Service and Project (own records are enforced by the permission
# hooks below and the controllers) and create-only on Proposal. Requests and
# proposal status changes go through inquiries/api.py and freelance/api.py,
# never /api/resource. Guest has no DocPerm on Profile, Service or Project:
# the public site reads them through the modules' public_api.
fixtures = [{"dt": "Role", "filters": [["name", "=", "Marketplace Moderator"]]}]

permission_query_conditions = {
	"Marketplace Profile": "marketplace.marketplace.permissions.profile_query_conditions",
	"Marketplace Service": "marketplace.marketplace.permissions.service_query_conditions",
	"Marketplace Project": "marketplace.freelance.permissions.project_query_conditions",
	"Marketplace Proposal": "marketplace.freelance.permissions.proposal_query_conditions",
	"Marketplace Inquiry": "marketplace.inquiries.permissions.inquiry_query_conditions",
}

has_permission = {
	"Marketplace Profile": "marketplace.marketplace.permissions.has_profile_permission",
	"Marketplace Service": "marketplace.marketplace.permissions.has_service_permission",
	"Marketplace Project": "marketplace.freelance.permissions.has_project_permission",
	"Marketplace Proposal": "marketplace.freelance.permissions.has_proposal_permission",
	"Marketplace Inquiry": "marketplace.inquiries.permissions.has_inquiry_permission",
}

# Cross-module reactions. Search indexing and gamification listen to the
# records other modules own; the owners never import them. Gamification hooks
# catch and log their own errors, so they never block the save.
doc_events = {
	"Marketplace Category": {
		"on_update": "marketplace.marketplace.public_api.metadata.clear_cache",
		"on_trash": "marketplace.marketplace.public_api.metadata.clear_cache",
	},
	# The public profile link follows the owner's username.
	"User": {
		"validate": "marketplace.marketplace.profile_handle.check_username",
		"on_update": "marketplace.marketplace.profile_handle.sync_profile_handle",
	},
	"Marketplace Specialty": {
		"on_update": "marketplace.marketplace.public_api.metadata.clear_cache",
		"on_trash": "marketplace.marketplace.public_api.metadata.clear_cache",
	},
	"Marketplace Profile": {
		"on_update": [
			"marketplace.search.indexing_service.on_profile_update",
			"marketplace.gamification.service.on_profile_update",
		],
		"on_trash": "marketplace.search.indexing_service.on_profile_delete",
	},
	"Marketplace Service": {
		"on_update": [
			"marketplace.search.indexing_service.on_service_update",
			"marketplace.gamification.service.on_service_update",
		],
		"on_trash": "marketplace.search.indexing_service.on_service_delete",
	},
	"Marketplace Project": {
		"on_update": "marketplace.search.indexing_service.on_project_update",
		"on_trash": "marketplace.search.indexing_service.on_project_delete",
	},
	"Marketplace Inquiry": {
		"on_update": "marketplace.gamification.service.on_request_update",
	},
	"Marketplace Proposal": {
		"on_update": "marketplace.gamification.service.on_proposal_update",
	},
}

scheduler_events = {
	# Raw activity (views, searches, clicks) is kept 90 days; daily metrics stay.
	"daily": ["marketplace.activity.events.purge_old_activity"],
}
