---
name: writing-line-naming-flattened-0826
description: 2026-08-26 写作课线三项命名/结构调整（配套件改 -X用、打包目录单层平铺、PPT 文件名带课次段），含 anim.json 必须同批改名与 Windows glob 分隔符两个坑
metadata:
  type: project
---

2026-08-26 用户拍板三项，**只动写作课线**（读书会与看图写话线的打包子文件夹、PPT 命名都不动）：

| 项 | 旧 | 新 |
|---|---|---|
| 配套件后缀 | `-学生合订 / -教师合订 / -家长合订` | `-学生用 / -教师用 / -家长用` |
| 打包目录 | `课件PPT\ 配套物料\` 两层子文件夹 | **单层平铺**，全部躺课次根目录 |
| PPT 文件名 | `<题目>-全课.pptx` | `<年级册>-第N单元-<题目>-课件PPT.pptx` |

存量一次到位：配套 90 个文件（30 个 `_data.json` git mv + 60 个 html/pdf 重渲）、
PPT 23 个（12 pptx + 11 anim.json）、10 个打包目录删了重打。

**第三项推翻了 `CLAUDE.md` §7 那条「PPT 文件名内仍是纯题目、不带年级单元」**（0802 立的）。
连带 [[writing-line-filename-unit-segment]]、[[writing-materials-pages-trimmed-0803]]、
[[writing-ppt-external-plus-animation]] 三条记忆都加了推翻戳。

**★ 最危险的一条：pptx 与 anim.json 必须同批原子改名**

`inspect_pptx.py:166-174` 的防覆盖闸门，键就是从 pptx 名派生的 `-anim.json` 路径：
只改 pptx 不改 anim.json → 闸门查一个不存在的文件 → `isfile` 为 False →
**静默生成全新的几何启发式工作单**，人工排了几十页的分组全部作废，一个错都不报。
`animate_pptx.py` 的 `slide_count` 校验拦不住（页数没变）。改完务必跑一次 `inspect_pptx.py` 验收：它**应该直接 sys.exit 报「已经过审查/人工校正」**——若开始输出新工作单，就是脱钩了。

⚠ **但验收只能拿「确知已审查过」的课次来跑**，这一步我当场踩了：闸门的条件是 `old.get("audit") or old.get("lesson_plan")`，**没做过审查的工作单它一律放行**，于是我随手拿《写日记》去验，脚本直接按几何启发式重写了那份 anim.json（462 行变动）。存量 12 份里有 4 份是装闸门（0806）之前做的、本来就没有 audit 字段——它们不受这道闸门保护。好在全程走 `git mv`，`git checkout -- <路径>` 从暂存区一键恢复。**验收固定用当天刚跑过 `audit_against_plan.py` 的那一课。**

另：`audit_against_plan.py` 会正常写回 `audit` 与 `plan_digest` 两个键（`slides` 分组数据一字不动），这是设计行为、不是被冲掉。改名后记得把每份 anim.json 的 `file` 字段也对齐新 pptx 名——它下游不回读、不影响功能，但留着旧名日后会误导。

**★ 我实际踩的坑：Windows 下 glob 返回反斜杠，`rstrip('/')` 是空操作**

批量改名脚本里写了 `os.path.basename(d.rstrip('/'))` 取课次名。glob 在 Windows 返回的是
`写作课件PPT输出\四上-第二单元-我的家人\`，`rstrip('/')` 去不掉尾部的 `\`，
`basename` 于是返回**空串**——23 个文件被改成了 `-课件PPT.pptx`，课次段整个丢了。
**取目录名一律用 `pathlib` 的 `.name`**（或 `os.path.basename(os.path.normpath(d))`）。

更值得记的是**为什么没当场发现**：我先跑了一遍预演，输出里明明白白印着 `→ -课件PPT.pptx`，
我把它看成了**列宽截断**。预演的价值全在逐行真看，扫一眼「格式像那么回事」等于没跑。
好在全程走 `git mv`，改回去只是再 mv 一次。

**★ 打包脚本没有任何删除逻辑，改结构必须手动清存量**

三个 package_*.py 全是 `mkdir(exist_ok=True)` + `copy2`，搜 `rmtree`/`unlink`/`os.remove` 零命中，
SKILL.md 也明写「覆盖同名文件，不会删掉目标里你手动加的别的文件」。所以只改 `dest` 不清存量，
会变成「根目录一份 + 旧子文件夹一份」。`读书会整套文件打包输出\洞\阅读单\` 里那 19 个早期散张 PDF
就是这个机制留下的活标本（某次收窄 glob 后一直没清）。打包目录是 gitignore 的纯产物、源都在，
**直接删掉重打最干净**。

⚠ 另注意：重打时若对全部课次跑一遍，会给物料不全的课次也建出残包（只有 1-2 个文件）。
既有的 10 个包之外的不要打。

**代码改动只有两处实质**（其余全是文档口径）：

- `place_pptx.py:130` 是**唯一的命名生成点**，`name = "%s-课件PPT.pptx" % unit`（unit 即课次标识，
  不再取 `unit.split("-")[-1]` 的纯题目）；合一与否不再影响文件名，只影响提示语。
- `place_pptx.py` 的 `claim()` **精确匹配改双键**：`key in (u, t)`。规范名剥噪后得到的是课次标识，
  只比纯题目的话会从精确跌到双向子串——而 `写日记`/`写观察日记`、`续写故事`/`缩写故事`
  这类互为子串的题目已经存在，模糊匹配迟早撞车。

**免疫点（查过，确实不用改）**：`plan_link.py:unit_of()` 取**父目录名**、
`package_writing.py` 按**目录** glob + `*` 全通配、`pageback_annotate.py` 的 `-页标映射.json`
派生自**详案 .md** 而非 pptx（故页标映射本次没跟着改名）、`build_ppt.py` 的 PROFILES
只做 renderer 分派 → **读书会线零波及**。

**回归闸门**：配套改名靠 `validate_packs.py` 的 **E24**（校验 `student_bundle` 路径存在），
10 个包的该字段改漏一个就 FAIL。改完还要 `build_deploy.py` 重打部署包。

**别忘了 `shots.json`**：宣讲件截图工单里硬编码了 6 条配套 pdf 路径 + 3 条 pptx 路径，
是全仓**唯一会静默失效**的地方（找不到源只会少出图，不报错）。改完用
「12 条 src 逐条 `os.path.exists`」验一遍。

相关：[[two-person-sync-0820]] · [[external-pptx-duplicate-drop-0825]]
