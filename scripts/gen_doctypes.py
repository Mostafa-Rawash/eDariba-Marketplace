"""Regenerate docs/DOCTYPES.md from the DocType JSON files.

Run from the repo root after any schema change:
  python scripts/gen_doctypes.py
Optional arguments: <doctype dir> <output file>.
"""

import glob
import json
import os
import sys

DOCTYPE_DIR = sys.argv[1] if len(sys.argv) > 1 else "marketplace/marketplace/doctype"
OUT = sys.argv[2] if len(sys.argv) > 2 else "docs/DOCTYPES.md"

BREAKS = {"Section Break", "Column Break", "Tab Break"}
TICK = "✓"


def tick(value) -> str:
	return TICK if value else ""


def anchor(name: str) -> str:
	return name.lower().replace(" ", "-")


def load_all() -> list[dict]:
	docs = [json.load(open(p, encoding="utf8")) for p in glob.glob(os.path.join(DOCTYPE_DIR, "*", "*.json"))]
	return sorted((d for d in docs if d.get("doctype") == "DocType"), key=lambda d: d["name"])


def data_fields(doc: dict) -> list[dict]:
	return [f for f in doc.get("fields", []) if f["fieldtype"] not in BREAKS]


def render(doc: dict) -> list[str]:
	out = [f"## {doc['name']}", ""]
	if doc.get("description"):
		out += [doc["description"], ""]
	out.append(f"- **Module:** `{doc.get('module', '')}`")
	if doc.get("autoname"):
		out.append(f"- **Naming:** `{doc['autoname']}`")
	if doc.get("title_field"):
		out.append(f"- **Title field:** `{doc['title_field']}`")
	if doc.get("istable"):
		out.append("- **Child table:** `Yes`")
	if doc.get("track_changes"):
		out.append("- **Track changes:** `Yes`")
	if doc.get("sort_field"):
		out.append(f"- **Sort:** `{doc['sort_field']} {doc.get('sort_order', 'DESC')}`")
	out += [
		"",
		"| Fieldname | Label | Type | Options | Required | Unique | Default | In list | Read only |",
		"|---|---|---|---|---|---|---|---|---|",
	]
	for f in doc.get("fields", []):
		if f["fieldtype"] == "Column Break":
			continue
		if f["fieldtype"] in BREAKS:
			out.append(f"| _{f.get('label') or f['fieldname']}_ ({f['fieldtype']}) | | | | | | | | |")
			continue
		options = ", ".join(o for o in (f.get("options") or "").split("\n") if o)
		out.append(
			f"| `{f['fieldname']}` | {f.get('label', '')} | {f['fieldtype']} | {options} | {tick(f.get('reqd'))} "
			f"| {tick(f.get('unique'))} | {f.get('default', '')} | {tick(f.get('in_list_view'))} | {tick(f.get('read_only'))} |"
		)
	perms = doc.get("permissions") or []
	if perms:
		out += ["", "**Permissions**", "", "| Role | Read | Write | Create | Delete | If owner |", "|---|---|---|---|---|---|"]
		for p in perms:
			out.append(
				f"| {p['role']} | {tick(p.get('read'))} | {tick(p.get('write'))} | {tick(p.get('create'))} "
				f"| {tick(p.get('delete'))} | {tick(p.get('if_owner'))} |"
			)
	out.append("")
	return out


def main():
	docs = load_all()
	lines = [
		"# Marketplace DocTypes",
		"",
		"Generated from the DocType JSON definitions in `marketplace/marketplace/doctype/` by "
		"`scripts/gen_doctypes.py`. Regenerate after schema changes rather than editing by hand.",
		"",
		f"{len(docs)} DocTypes.",
		"",
		"| DocType | Module | Naming | Child table | Fields |",
		"|---|---|---|---|---|",
	]
	for d in docs:
		lines.append(
			f"| [{d['name']}](#{anchor(d['name'])}) | {d.get('module', '')} | {d.get('autoname') or ''} "
			f"| {'Yes' if d.get('istable') else 'No'} | {len(data_fields(d))} |"
		)
	lines.append("")
	for d in docs:
		lines += render(d)
	with open(OUT, "w", encoding="utf8", newline="\n") as fh:
		fh.write("\n".join(lines).rstrip("\n") + "\n")


if __name__ == "__main__":
	main()
