---
name: writing-materials-handedits-lost-on-rerender
description: 配套物料的文字手改若只改 HTML 没回写 _data.json，下次重渲即被静默冲掉（0817 已实际发生一次）
metadata:
  type: project
---

写作配套物料（writing-materials 三侧合订件）的链路是 `_data.json` → HTML → PDF。**改 HTML 等于改产物**：下一次重渲从 json 出发，手改全部消失，且不报错、不冲突、无任何提示。

2026-08-17 那次为修 Type3 字体（去 `✍` 等 emoji）做的批量重渲，就把 8/5–8/15 期间攒下的一批手改文字整体冲回了 json 原文。2026-08-21 才被发现——用户手里的旧 PDF 比新 PDF 文字更好，是因为旧的才是手改版。

**Why**：json 入库、HTML/PDF 不入库（§8），所以手改在 HTML 上既没有版本记录、也不参与双人同步，只活在某台机器的产物文件里，重渲一次就没了。

**How to apply**：
- 配套物料的任何文字修改**一律回写 `_data.json`**，改完重渲；不要在 HTML 或 PDF 上直接改。
- 怀疑某份产物含未回写手改时，判据＝**提取 PDF 文本与同目录 `_data.json` 比对措辞**，不一致即是手改（json 自身有 git 历史可查是否变动过）。
- 已经只剩产物、源已丢的情况下，补版式而不动正文的可靠做法：PyMuPDF 用 `page.show_pdf_page(rect, src, pno, clip=...)` 从新版 PDF **原位抠取**局部（字体/颜色/线宽全部继承，不依赖本机字体），整页新增用 `doc.insert_pdf(src, from_page=n, to_page=n, start_at=k)`。0821 给 z 盘 8 份学生合订件补「姓名栏＋续页」就是这么做的。

⚠ **遗留风险**：仓库内 9 个课次的学生合订 `_data.json` 仍是不含那批手改的版本，日后任何重渲都会再次得到无手改版。用户 0821 明确说这次只改他给的 z 盘目录、不动仓库，所以没回填。

相关：[[writing-materials-skill-student-bundle]] · [[writing-materials-pages-trimmed-0803]] · [[pdf-type3-fonts-fixed]]
