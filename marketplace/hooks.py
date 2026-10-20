from . import __version__ as app_version  # noqa: F401

app_name = "marketplace"
app_title = "eDariba Marketplace"
app_publisher = "eDariba"
app_description = "Accountant directory, services marketplace, and freelance project marketplace for eDariba."
app_email = "dev@edariba.com"
app_license = "proprietary"

# The only role this app adds. "Marketplace Moderator" verifies profiles, moderates
# listings, and reads all requests in Desk. "System Manager" already covers full admin.
#
# There are deliberately no provider/client roles: what a user can do in the
# marketplace comes from their records (a Marketplace Profile they own, with its
# offers_services / accepts_projects switches; requests they sent), and every
# write by a normal user goes through api/workspace.py, never /api/resource.
fixtures = [{"dt": "Role", "filters": [["name", "=", "Marketplace Moderator"]]}]

permission_query_conditions = {
	"Marketplace Profile": "marketplace.marketplace.permissions.profile_query_conditions",
	"Marketplace Service": "marketplace.marketplace.permissions.service_query_conditions",
	"Marketplace Project": "marketplace.marketplace.permissions.project_query_conditions",
	"Marketplace Proposal": "marketplace.marketplace.permissions.proposal_query_conditions",
	"Marketplace Inquiry": "marketplace.marketplace.permissions.inquiry_query_conditions",
}

has_permission = {
	"Marketplace Profile": "marketplace.marketplace.permissions.has_profile_permission",
	"Marketplace Service": "marketplace.marketplace.permissions.has_service_permission",
	"Marketplace Project": "marketplace.marketplace.permissions.has_project_permission",
	"Marketplace Proposal": "marketplace.marketplace.permissions.has_proposal_permission",
	"Marketplace Inquiry": "marketplace.marketplace.permissions.has_inquiry_permission",
}

doc_events = {
	"Marketplace Category": {
		"on_update": "marketplace.api.public.metadata.clear_cache",
		"on_trash": "marketplace.api.public.metadata.clear_cache",
	},
	"Marketplace Profile": {
		"on_update": "marketplace.services.indexing_service.on_profile_update",
		"on_trash": "marketplace.services.indexing_service.on_profile_delete",
	},
	"Marketplace Service": {
		"on_update": "marketplace.services.indexing_service.on_service_update",
		"on_trash": "marketplace.services.indexing_service.on_service_delete",
	},
	"Marketplace Project": {
		"on_update": "marketplace.services.indexing_service.on_project_update",
		"on_trash": "marketplace.services.indexing_service.on_project_delete",
	},
}
