# -*- coding: utf-8 -*-
"""把原型两份脚本里的数据导出为 skill 的标准 manifest.json（剥离 logo）。"""
import json, pathlib
import make_sheets, make_graphics

KEY = {"template_table.html": "table", "template_venn.html": "venn",
       "template_ladder.html": "ladder", "template_logic.html": "logic",
       "template_voyage.html": "voyage"}

def strip(d):
    return {k: v for k, v in d.items() if k not in ("file", "logo")}

sheets = []
# 表格类：SHEETS 条目本身即 data（含 file）
for s in make_sheets.SHEETS:
    sheets.append({"file": s["file"], "template": "table", "data": strip(s)})
# 图形类：JOBS 条目为 {file, template(html), w, h, data}
for j in make_graphics.JOBS:
    sheets.append({"file": j["file"], "template": KEY[j["template"]],
                   "data": strip(j["data"])})

manifest = {"book": "格列佛游记", "sheets": sheets}
out = pathlib.Path("e:/laojohn-lesson-plan/.claude/skills/laojohn-reading-sheet/"
                   "examples/格列佛游记-manifest.json")
out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", out, "·", len(sheets), "sheets")
