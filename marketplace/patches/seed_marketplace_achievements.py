"""Starting achievement definitions (Marketplace Achievement). Moderators can
edit or deactivate them from the desk. Re-running adds missing codes only.

Definitions only: nobody is awarded anything here. Users reach achievements
the next time an event triggers evaluation (services/gamification.py).
"""

import frappe

ACHIEVEMENTS = [
	("profile-complete", "ملف مكتمل", "أكملت كل عناصر ملفك المهني.", "profile_complete", 1, 10),
	("first-service", "أول خدمة", "نشرت أول خدمة لك في السوق.", "services_published", 1, 20),
	("responsive-10", "سريع الاستجابة", "رددت على ١٠ طلبات.", "requests_responded", 10, 30),
	("completed-5", "خمس مهام منجزة", "أغلقت ٥ طلبات بعد قبولها.", "requests_completed", 5, 40),
	("first-hire", "أول عرض مقبول", "قُبل أول عرض قدمته على مشروع.", "proposals_accepted", 1, 50),
]


def execute():
	for code, title, description, metric, threshold, order in ACHIEVEMENTS:
		if frappe.db.exists("Marketplace Achievement", code):
			continue
		frappe.get_doc(
			{
				"doctype": "Marketplace Achievement",
				"code": code,
				"title": title,
				"description": description,
				"metric": metric,
				"threshold": threshold,
				"sort_order": order,
			}
		).insert(ignore_permissions=True)
