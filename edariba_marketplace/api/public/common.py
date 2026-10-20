"""Standard response envelope shared by every Marketplace endpoint.

No pre-existing Frappe API envelope convention was found in this app (it did
not exist before this task — see the audit note in README.md), so the
envelope below follows the task brief's own contract exactly rather than
inventing a third shape.
"""

from typing import Any

import frappe


def ok(data: Any, page: int | None = None, page_size: int | None = None, total: int | None = None, meta: dict | None = None) -> dict:
	out: dict[str, Any] = {"success": True, "data": data}
	if page is not None:
		out["pagination"] = {
			"page": page,
			"page_size": page_size,
			"total": total,
			"has_more": (page * page_size) < total if total is not None else False,
		}
	out["meta"] = meta or {}
	return out


def not_found(message: str):
	frappe.local.response["http_status_code"] = 404
	return {"success": False, "data": None, "meta": {}, "error": message}
