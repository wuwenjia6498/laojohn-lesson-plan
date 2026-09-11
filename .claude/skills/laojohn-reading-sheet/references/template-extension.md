# 如何加第 N 种模板（扩展机制）

> 2026-07-27 由 SKILL.md 下沉，本文件为模板扩展机制唯一源。日常生成阅读单不需要读本文件；只在现有 18 种模板覆盖不了、要新增模板时读。

现有 18 种覆盖不了的可视化工具(如环形故事地图、多级括号思维导图、坐标轴/四象限图)，按固定四步加，**不动引擎**：

1. **新建** `templates/template_<键>.html`，照抄 `templates/template_base.html` 骨架，只实现中间主体区——自然满足「模板契约」(注入点 `/*__DATA__*/ null`、根 `#page` 宽 794、渲染完置 `body[data-rendered='1']`、白底+右上 logo+标题下移+左上版本角标)。
2. **登记**：SKILL.md「模板登记表」加一行(模板键 / 文件 / 用途 / 命中信号)。
3. **加识别规则**：`references/archetype-decision.md` 加该工具的命中条件与归类。
4. **补字段说明**：`references/data-schema.md` 加该模板的 JSON schema。

`render.py` 只按 manifest 里 `template` 字段加载 `template_<键>.html`，所以**加模板=加一个守契约的 html + 登记表加一行**，引擎与已有模板零改动。

> **若同时维护 PPTX 输出**：新模板还需在 `scripts/render_pptx.py` 的 `RENDERERS` 里注册一个 `render_<键>(slide, d)`(直接搬该 HTML render() 的像素坐标常量、按 `px→EMU` 复刻)；否则该模板的 PPTX 页会渲成「缺 renderer」占位提示。PDF 路径不受影响。

> 优先判断：很多"新样式"其实只是现有原型换参数(3 圈维恩、5 阶阶梯、任意列表格)——这种**只改 data、不加模板**。真正结构不同的才走上面四步。

> **历史说明（勿与新 PPTX 输出混淆）**：曾有 `scripts/ppt_export.py` 把阅读单渲成「空白图 + 逐格答案小图」供 `laojohn-ppt` 的 `阅读单` 页型复用。因阅读单版式过多、破坏 PPT 排版一致性，该页型已下线——阅读单内容在 PPT 端改回**统一填空表格**呈现（答案 `{{}}` 标记、逐格点击，见 laojohn-ppt SKILL.md）。`ppt_export.py` 已删除；模板里残留的 `data-answer/data-content` 标注无害（不影响打印），保留即可，新模板无需再加。
>
> **本技能的 `render_pptx.py` 与上面那条无关**：它不是「阅读单塞进投屏课件」，而是把**阅读单本身**另出一份**老师可编辑的 PPTX 交付物**(原生形状/表格，独立于 laojohn-ppt、不耦合)，是 PDF/HTML 之外的第三种成品。
