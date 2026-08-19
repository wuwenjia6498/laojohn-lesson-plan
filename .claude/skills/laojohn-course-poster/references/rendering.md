# 渲染机制与版式说明

## 工作原理

`scripts/render_poster.py` + `assets/template.html` 配合完成渲染。

1. 脚本读 `data.json`,按 `title` 去 `covers/` 匹配封面,把数据 + 封面 + 二维码(均转 data URI)内联进模板,生成自包含 HTML。
2. 模板用**纵向流式布局**(flex column),各块自然堆叠,块间用 margin 控间距。**不写死任何块的坐标**——删块/改字时下方自动上移收拢。
3. JS 渲染完给 `<body>` 打 `data-rendered="1"`;脚本等到该标志再截图。
4. 用 Chromium 截 `#page` 元素的完整范围导出 JPG,宽 1242px,高度随内容自适应,`device_scale_factor=2`(2x 高清)。

## 版式分区(自上而下)

1. **头部图(含信息卡空壳)**:`assets/header.jpg` 是一张固定背景图,画死了品牌页眉(老约翰® 深度阅读 + 读书会胶囊)**以及信息卡的外壳**(红底、粉色标签条、白底值区、左下三角)。基准尺寸 1280×1071。
   - 信息卡内容区(叠加文字处):原图 y 500–1032;粉色标签条 x 28–248;白底值区 x 248→。
   - 模板用 `.info-overlay` 绝对定位(百分比贴合图片),把 7 行书目文字、封面图、L 等级角标**叠加**到这张图上。底色/边距/圆角都在图里,代码不画,只填内容。
2. **内容大卡**:白底大圆角,获奖块(并入顶部)+ 四栏目(内容简介/阅读收获/阅读策略学习&运用/可视化思维工具学习&运用),小标题粉色胶囊;右下角二维码 + 「详情扫码咨询」。

**换头部图须同步改坐标**:若更换 `header.jpg`(不同尺寸或信息卡位置变化),需重新标定 `.info-overlay`/`.info-left`/`.info-cover-wrap` 的百分比。标定方法:用 PIL 横扫/竖扫找粉-白-红分界像素,除以图宽/图高得百分比。

## 配色变量(template.html 的 :root)

| 变量 | 值 | 用途 |
|---|---|---|
| `--brand` | `#E8553A` | 主品牌红(页面底色) |
| `--card-bg` | `#ffffff` | 信息卡 / 内容卡白底 |
| `--card-tri` | `#F6D9CF` | 信息卡左下三角缺口浅粉 |
| `--pill-bg` | `#F6CFC3` | 小标题粉色胶囊底 |
| `--pill-ink` | `#C23A22` | 小标题胶囊文字 |
| `--award-ink` | `#2F6FB0` | 获奖蓝字 |
| `--placeholder-bd` | `#E8553A` | 占位框虚线描边(醒目=待人工处理) |
| `--placeholder-bg` | `#FBEAE5` | 占位框浅底 |
| `--page-w` | `1242px` | 朋友圈/社群长图标准宽 |

改色只需改这几个变量。占位框样式醒目是**有意为之**——它提示人工此处待回填,不要为了好看把它弱化。

## 占位框逻辑(template.html 的 isPlaceholder)

模板里 `isPlaceholder(s)` 判断一个值是否为占位:满足以下任一即视为占位,包成红色虚线框:
- 形如 `【…】`(C 类未填)
- 含 `____` 或 `请回填`(B 类占位)

所以:AI 把 C 类填实后,`【…】` 消失,该栏正常显示;人工把 B 类回填后,占位框变正常文字。

## 字体

依赖系统中文字体(本环境已装 Noto Sans CJK)。字体栈:`"Noto Sans CJK SC","Source Han Sans SC","Microsoft YaHei",sans-serif`。Chromium 截图字体自动渲染,无乱码。

## 环境依赖

- `playwright`(Python 包)+ Chromium。Chromium 装在 `%LOCALAPPDATA%\ms-playwright`(用户名无关,脚本按当前用户主目录解析),环境变量 `PLAYWRIGHT_BROWSERS_PATH` 约定见根 CLAUDE.md §1。
- 换环境:`pip install playwright` 再 `python -m playwright install chromium`。
- 生成占位封面/占位二维码用到 `Pillow`(PIL)。

## 资产清单(assets/)

| 文件 | 状态 | 说明 |
|---|---|---|
| `header.jpg` | 已就绪 | **固定头部图,含品牌页眉 + 信息卡空壳**(红底/粉条/白框/三角)。书目文字、封面、L角标由代码叠加。换图须重标坐标(见上)。 |
| `template.html` | 已就绪 | 海报模板 |
| `covers/_placeholder.jpg` | 已就绪 | 占位封面(品牌色) |
| `covers/<书名>.jpg` | **用户维护** | 真实书封,按书名命名,自行放入 |
| `qrcode.png` | **待用户提供** | 正式咨询二维码;缺失时用占位二维码 |

## 版式常见问题

- **文字过长撑破版面**:回到萃取压短 C 类文案,不要改版式。
- **信息卡某行占位框换行**:占位文案本身较长属正常,人工回填后会变短。
- **页眉/文案微调**:页眉文案在模板里写死(品牌固定),书目和内容文案来自 JSON。
