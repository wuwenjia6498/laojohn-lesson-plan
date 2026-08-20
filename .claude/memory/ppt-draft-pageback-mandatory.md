---
name: ppt-draft-pageback-mandatory
description: PPT链产出后详案页标回注从「按需」升级为必做，并须重渲详案docx（2026-07-18用户拍板）
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 45bdcef7-bec3-4727-b790-d8469fed87b1
  modified: 2026-07-18T07:51:11.573Z
---

2026-07-18 用户拍板：跑完 ppt-draft→ppt 链后，**详案页标回注（〖PPT 第N页 · 页型 · 眉标〗）不再是「按需」项，必做、不等用户点名**；回注改了详案 .md，必须随后用 `laojohn-lesson-plan/assets/md_to_laojohn_docx.py` 重渲详案 .docx。

**Why:** 老师备课要对着详案就能知道讲到课件第几页；只出 PPT 不回注，详案与课件脱节。用户在呼兰河传 PPT 链交付后追问「有没有补换页点」并明确要求固化。

存量补齐（2026-07-18 同日）：呼兰河传 69 标、彼得潘 76 标、玛丽阿姨 84 标、汉修先生 65 标、独一无二的伊凡 82 标，五本详案 md+docx 均已带页标；其余存量书（洞/俗世奇人/骑鹅等）尚未回注。

**How to apply:** 已固化进 `laojohn-ppt-draft/SKILL.md`（工作流程第 6 步标「必做」、第 8 步交付含回注详案 md+docx、自检清单新增页标项）；规则细节仍以 `references/detail-pageback-annotation.md` 为唯一源（幂等先清旧标、封面/END 不标、每课时从第2页起）。注意：详案 docx 常被 WPS/Word 后台占用报 PermissionError，重渲前请用户关闭文档（呼兰河传两次踩中）。用户口中的「换页点」在现行体系里指的就是页标回注，勿误解为已废弃的 `【PPT换页-Pxx】`。
