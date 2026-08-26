---
name: promo-materials-render-chain
description: 写作课对外宣传件（家长端海报／馆内海报／课程总地图）的源与渲染链，含「PDF 反查源」的三条指纹判据与一次误判无源的代价
metadata:
  type: project
---

`写作课相关宣传文件\` 下的对外物料不属任何 laojohn-* skill 线，此前没有渲染入口，
2026-08-26 收四上换题尾时补齐。**改文案一律只改源，禁止去手改 PDF。**

| 产物 | 源 | 怎么重渲 |
|---|---|---|
| `家长端海报.pdf`（360×1760.88pt 手机窄长图） | `家长端海报.html`（`.page{max-width:480px}`） | `python render_promo_html.py 家长端海报` |
| `馆内海报.pdf`（A4 横版 842.88×595.92pt） | `馆内张贴海报.html`（`.sheet{width:297mm}`） | `python render_promo_html.py 馆内海报`（**scale 必须 0.98**，1.0/0.99 都溢出第 2 页） |
| `同步习作课程总地图.docx/.pdf` | **无 md 源**，docx 自己就是源 | 改 docx 的 `word/document.xml`（文本不跨 run），pdf 走 Word COM 重导 |
| `招生海报.pdf` | **孤儿件**，与现存任何 html 都不对应 | 不管它（见下） |

`render_promo_html.py` 在**仓库根**（与 fix_quotes_md.py 同级），差异全在顶部 `PROFILES` 表；
两种输出模型 `tall`（量 scrollHeight 出单页动态高）／`fixed`（给定纸张 + scale）。
**不复用 `laojohn-reading-guide\scripts\_a4_render.py`**——那件是 data.json ＋ 模板注入驱动、
宽度硬编码 794px，且是读书会下游三家的单一源，塞宣传件进去就是把两种输出模型混进一个引擎。

**★ 教训：先反查源，再决定手改（2026-08-26 实付代价）**

当时判定「家长端海报无 html 源、只能手改」，用 PyMuPDF redaction + TextWriter 原位重排了两行。
代价三项：**体积 391 KB → 12.8 MB**（TextWriter 用 fontfile 嵌的是整套微软雅黑、不做子集；
一份要发给家长的海报，微信发不动）、**文字层阅读顺序错乱**（新写的行落到内容流末尾）、
**下次改文案还得再手改一遍**。而源一直都在——只是导出时改了文件名，它当时叫 `招生海报.html`。

**判 PDF 有没有源，三条指纹，任一条就能定位：**

1. **页宽换算**：`MediaBox` 宽 ÷ 0.75 ＝ css px，拿去 grep 全仓 html 的 `max-width`／`width`。
   360pt → 480px，全仓唯一命中，这一条最快。
2. **producer**：`Skia/PDF mNNN` ＝ headless Chromium 打印（有脚本渲过）；
   `Chrome/NNN` 那种带完整 UA 的 ＝ 人在浏览器里手工另存，多半没有可复现的源。
3. **内嵌字体 + 图像数**：headless Windows 下 `PingFang SC` 会回落成 `MicrosoftYaHei`；
   图像 XObject 数应与 html 里 `data:image` 的处数吻合。

定位到候选后，**用文本重合率坐实**：html 剥标签取可见文本块，逐块在 pdf 文本里查——
当时是 99/99 零差异。别只凭一两句话命中就下结论。

**孤儿件 `招生海报.pdf`**：0817 生成，正文仅 162 字（现 html 有 1179 字），内嵌 ZCOOL 字体 + 14 张图，
producer 是 `Chrome/150`，正文还残留上传控件的 “or browse files”。它是更早的另一版设计、无源可复现，
**用户拍板原样留着不动**，不要试图用哪个 html 去覆盖它。html 已改名为 `家长端海报.html` 与产物对齐。

**gitignore 口径已变（0826）**：`写作课相关宣传文件/**` 整目录仍忽略，但例外从 `*.md`/`*.json`
扩到 **`*.html`**——两份海报 html 完全自包含（logo 内嵌 base64、零外链），是重渲不出来的源，
按本仓「重渲得出来才不入库」的判据该入库。pdf/docx 照旧忽略。
**不放行 html 的后果是实打实的**：同事那台机器只有旧 pdf、没有源，改文案只能去手改 pdf，
正是上面那个坑的复发路径。参见 [[two-person-sync-0820]]、[[writing-materials-handedits-lost-on-rerender]]。
