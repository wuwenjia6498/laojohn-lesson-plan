# 渲染机制与排版说明

## 工作原理

`scripts/render_pdf.py` + `assets/template.html` 配合完成渲染。核心技巧:**不写死任何节点坐标**。

1. 脚本把 `data.json` 内联进模板的 `DATA` 变量,生成自包含 HTML。
2. 模板用 CSS Grid 三列布局(中心 / 一级分支 / 子节点),所有节点是真实 DOM,**高度随文字自适应**。
3. 节点排布完成后,JS 用 `getBoundingClientRect()` **实测每个节点的真实位置**,再用 SVG 三次贝塞尔曲线连接父子节点的右缘→左缘。
4. 画完连线给 `<body>` 打上 `data-rendered="1"`;脚本等到这个标志再导出,确保连线已就位。
5. 页面为竖向 A4(794×1123 @96dpi);若内容超过一页高度,量出实际高度按此导出,避免截断。

弧线两端各留 `GAP`(模板顶部常量,默认 5px)与节点的水平间隙,文字块再加左内边距,确保线头不贴字。

因此:节点文字再长、条数再多,连线起止点都自动对齐。**调整内容时改 JSON 即可,不要去模板里填坐标。**

## 配色变量(template.html 的 :root)

米褐色系,对齐样张:

| 变量 | 值 | 用途 |
|---|---|---|
| `--root-bg` | `#BF826F` | 中心节点底色 |
| `--branch-bg` | `#D1B397` | 一级分支底色 |
| `--line` | `#c7a98a` | 连线颜色 |
| `--header-ink` | `#B8B8B8` | 页眉文字 |
| `--rule` | `#B8B8B8` | 页眉下划线 |
| `--leaf-ink` | `#4a443f` | 叶节点文字 |

改色只需改这几个变量,连线颜色由 JS 从 `--line` 读取,会同步。

## 字体

依赖系统中文字体(本环境已装 Noto Sans/Serif CJK)。模板字体栈:`"Noto Sans CJK SC", "Source Han Sans SC", "Microsoft YaHei", sans-serif`。PDF 由 Chromium 打印,字体自动嵌入,不会出现方框乱码。

## 环境依赖

- `playwright`(Python 包)+ Chromium。Chromium 装在 `%LOCALAPPDATA%\ms-playwright`(用户名无关,脚本按当前用户主目录解析),环境变量 `PLAYWRIGHT_BROWSERS_PATH` 约定见根 CLAUDE.md §1。
- 若换环境,先 `pip install playwright` 再 `python -m playwright install chromium`。
- 检查 PDF 时可用 `pdf2image`(依赖系统 `poppler-utils`)把 PDF 转 PNG 肉眼核对。

## 排版常见问题

- **某行文字过长把页面撑宽/换行难看**:首选回到萃取把说明句压短(理解类节点说明保持一行)。确需容纳长文,可调 `.l3 / .leaf` 的 `max-width`。
- **某分支子节点过多导致竖向拥挤**:Grid 的 `.children-col` 用 `justify-content: space-around` 自动分布;若仍挤,适当减少该分支节点数(教学流程只需勾勒环节、不必穷尽小节)。
- **页眉/标题文案**:在模板里写死的是结构,文案来自 JSON 的 `header_left / header_right / title`。

## 输出

- `<basename>.pdf`:最终交付。
- `<basename>.html`:可编辑源文件,数据已内联,可直接浏览器打开或改 `DATA` 后用脚本重渲染。
