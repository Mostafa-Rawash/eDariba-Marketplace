from . import __version__ as app_version  # noqa: F401

app_name = "edariba_marketplace"
app_title = "eDariba Marketplace"
app_publisher = "eDariba"
app_description = "Accountant directory, services marketplace, and freelance project marketplace for eDariba."
app_email = "dev@edariba.com"
app_license = "proprietary"

# Roles this app expects to exist (create via fixtures/patch, not here):
#   "Marketplace Moderator" — can verify profiles, moderate listings, read all inquiries.
# "System Manager" already covers full admin access; no separate "Marketplace Admin" role
# is introduced since System Manager already satisfies that need (fewer roles = fewer
# places for a permission rule to drift).

permission_query_conditions = {
	"Marketplace Profile": "edariba_marketplace.marketplace.permissions.profile_query_conditions",
	"Marketplace Service": "edariba_marketplace.marketplace.permissions.service_query_conditions",
	"Marketplace Project": "edariba_marketplace.marketplace.permissions.project_query_conditions",
	"Marketplace Proposal": "edariba_marketplace.marketplace.permissions.proposal_query_conditions",
	"Marketplace Inquiry": "edariba_marketplace.marketplace.permissions.inquiry_query_conditions",
}

has_permission = {
	"Marketplace Profile": "edariba_marketplace.marketplace.permissions.has_profile_permission",
	"Marketplace Service": "edariba_marketplace.marketplace.permissions.has_service_permission",
	"Marketplace Project": "edariba_marketplace.marketplace.permissions.has_project_permission",
	"Marketplace Proposal": "edariba_marketplace.marketplace.permissions.has_proposal_permission",
	"Marketplace Inquiry": "edariba_marketplace.marketplace.permissions.has_inquiry_permission",
}

doc_events = {
	"Marketplace Category": {
		"on_update": "edariba_marketplace.api.marketplace.metadata.clear_cache",
		"on_trash": "edariba_marketplace.api.marketplace.metadata.clear_cache",
	},
	"Marketplace Profile": {
		"on_update": "edariba_marketplace.services.marketplace.indexing_service.on_profile_update",
		"on_trash": "edariba_marketplace.services.marketplace.indexing_service.on_profile_delete",
	},
	"Marketplace Service": {
		"on_update": "edariba_marketplace.services.marketplace.indexing_service.on_service_update",
		"on_trash": "edariba_marketplace.services.marketplace.indexing_service.on_service_delete",
	},
	"Marketplace Project": {
		"on_update": "edariba_marketplace.services.marketplace.indexing_service.on_project_update",
		"on_trash": "edariba_marketplace.services.marketplace.indexing_service.on_project_delete",
	},
}
