"""Starting list for Marketplace Specialty, grouped by the category slugs the
WordPress marketplace uses. Moderators edit the list from the desk afterwards.
Re-running adds missing titles only; existing ones are left as they are."""

import frappe

SPECIALTIES = {
	"bookkeeping": ["مسك الدفاتر المحاسبية", "ميزان المراجعة", "التسويات البنكية", "التقارير المالية الدورية"],
	"tax": [
		"الفحص الضريبي",
		"إقرار القيمة المضافة",
		"ضريبة الدخل",
		"كسب العمل والمرتبات",
		"منازعات ولجان الطعن",
		"ضرائب التجارة الإلكترونية",
		"تسعير المعاملات",
	],
	"financial-statements": ["القوائم المالية الختامية", "معايير المحاسبة المصرية", "مراجعة وتدقيق الحسابات"],
	"company-formation": ["تأسيس الشركات", "إجراءات هيئة الاستثمار", "السجل التجاري والبطاقة الضريبية"],
	"feasibility": ["دراسات الجدوى", "النمذجة المالية", "ملفات التمويل البنكي"],
	"e-invoice": ["الفاتورة الإلكترونية", "الإيصال الإلكتروني", "تكويد الأصناف EGS و GS1", "ربط أنظمة ERP بمنظومة الضرائب"],
}


def execute():
	order = 0
	for category, titles in SPECIALTIES.items():
		linked = category if frappe.db.exists("Marketplace Category", category) else None
		for title in titles:
			order += 10
			if frappe.db.exists("Marketplace Specialty", title):
				continue
			frappe.get_doc(
				{
					"doctype": "Marketplace Specialty",
					"title": title,
					"category": linked,
					"sort_order": order,
				}
			).insert(ignore_permissions=True)
