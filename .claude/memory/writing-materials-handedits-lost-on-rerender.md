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

## 0904 补：用户手改 PDF 后「照着回贴源文件」的做法（五上《“漫画”老师》学生用实做）

用户在 PDF 编辑器里直接改了学生用 PDF，要求照着改源。**源是 `_data.json`，不是 markdown**（用户嘴上说的是「markdown 源文件」，别照字面去翻详案）；只有改动触及教学内容时才另外同步详案 .md。

比对法（本次 41 个字段里精准命中 3 处改动）：`pypdf` 提 PDF 全文 → 两边都 `re.sub(r'\s+','')` 去空白 → 逐个 json 字符串（先剥 `{b}`/`{hl}` 标记）判断是否为 PDF 文本的子串，不是即被改。**必须去空白再比**——PDF 提取会因字体子集切分（`/DAAAAA+MicrosoftYaHei` 与用户新输入文字用的 `/MicrosoftYaHei`）在词中间插入换行与空格，肉眼看像「借鉴 范文的写作方法」，实际原文无空格。

**判断用户是不是想加粗，用 `extract_text(visitor_text=…)` 读 `/BaseFont`**：本次用户在起笔提示里打了一个 markdown 式 `**`，visitor 显示那段全是 `MicrosoftYaHei`（非 `-Bold`），说明星号只是**字面字符、没被渲染成加粗**。而 `worksheet.draftnote` 在模板里走 `textContent`（不是 `rich()`），**富文本标记与星号都会原样印在学生打印件上**——所以回写时把 `**` 删掉，需要加粗得先改模板。支持 `{b}` 的字段只有 `worksheet.skills`、`essay.notes[].a`、`essay.method`、`essay.footer`（见 data_schema.md），别往别处塞。

**手改文字常常撑破页数闸门**：本次用户把 `essay.footer` 从 43 字改到 58 字，`.footer-skill` 的 p 被 badge 挤窄（可用宽约 600px、每行约 54 字），一变两行范文页立刻裂成 5 页。压回一行时**保留用户的全部意思、只压字数**，并把改动原句与落地句一并报给用户核对——不要默默改写他刚写下的话。

相关：[[writing-materials-skill-student-bundle]] · [[writing-materials-pages-trimmed-0803]] · [[pdf-type3-fonts-fixed]]
