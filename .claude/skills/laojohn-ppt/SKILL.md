---
name: laojohn-ppt
description: 把"老约翰深度阅读读书会"风格的课件中间稿 (.md) 编译为老师投屏用 .pptx；另承载写作课两条线：「仓内直出」（按母版从详案直接出带图带动画的 pptx）与「外部 PPT 后处理链」（认领归位→读详案审查 PPT→注入点击动画→详案页标回注，可选添图）。当用户要求"把课件中间稿做成 PPT""烘焙投屏课件"，"从详案直出 PPT""按母版出课件"，或说"PPT 放好了""外部 PPT 处理一下""新做的课件处理一下""这份 PPT 是外面做的，加下动画"时使用本技能。
---

# laojohn-ppt — 投屏 PPT 编译器 + 写作课仓内直出 + 外部 PPT 后处理链

两条用途，**按线走、别混用**：

| 线 | 走法 | 目录 |
|---|---|---|
| 读书会 | **编译**：中间稿 `.md` → `.pptx`（16:9，微软雅黑 + 宋体，零依赖） | `读书会课件PPT输出\` |
| 写作课·仓内直出（2026-09-26 起，重写详案的课次走这条） | **直出**：按母版写 dc.html → 转 pptx → 审查 → 动画 → 页标 | `写作课件PPT输出\` |
| 写作课·外部件（2026-08-03 起，存量课次） | **后处理链**：外部平台生成 pptx，本仓做归位/审查/动画/页标，可选添图 | `写作课件PPT输出\` |
| 宣讲（2026-08-24 起） | **编译**：宣讲中间稿 `.md` → `.pptx`（对外产品宣讲件，非课堂件） | `写作课相关宣传文件\<宣讲件名>\` |

## 何时使用

- "把中间稿做成 PPT""烘焙投屏课件"，或上游 `laojohn-ppt-draft` 刚出中间稿 → **编译**（见下方契约速览）
- **"从详案直出 PPT""按母版出课件"** → **仓内直出**（下一节）
- **"PPT 放好了""外部 PPT 处理一下""新做的课件处理一下""外面做的，加下动画"** → **后处理链**

---

## 仓内直出（写作课线 · 2026-09-26 起）

> 用户定：**以后重写详案的课次一律走直出**；外部件那条链留给存量课次。六上五是试点（直出件与外部配图终稿并存，终稿仍用外部配图版）。来历与踩过的坑见记忆 `writing-ppt-direct-build-pilot-0926`。

母版（规范单一源）在 `assets/writing-master/`：`framework.md` 是配色、骨架、版式库、文字、**本仓增补**（主题色胶囊＋吉祥物＋手指图标、§四之二 配图版式 9 条、§八 动画与核对、讲评环节不进 PPT）；`register-audit.md` 是起草后的语域审读清单。**写页面前整读 framework.md**。

1. **备图**（课件配图工具，gpt-image）：场景图走 `run_lesson.py`；要立在底带／页边的人物、每课的吉祥物（`抠-吉祥物`）一律 `gen_cutouts.py` 出透明底；**已有、已认可的图直接复用**。处理好的图放 `课件配图工具/课件产出/<课次>/gpt-image/ppt配图缓存/直出/`，吉祥物命名 `吉祥物.png`。
2. **写课件构建脚本** `写作课件中间稿输出/<课次>/<课次>-课件构建.py`（入库）：页序＝详案〖PPT第N页〗，用 `tools/writing_deck_kit.py` 的积木（cover／section_page／page／steps／bullets／card／strip／band／fig／worksheet_page／timer_badge／end_page）逐页写；点击分组写在 a／a0／fa 参数（按详案师话顺序、禁回跳）。范例＝六上五那份。写完做语域审读（register-audit.md）。
3. **一条龙出件**：`python .claude/skills/laojohn-ppt/tools/direct_build.py <课次>`——截稿纸（`grab_worksheet.py`）→ 跑构建脚本出 dc.html → `html_to_pptx.py` 转 pptx → `inspect_pptx.py` → `audit_against_plan.py`（审查闸门）→ 并入分组 → `animate_pptx.py` → 回读核验（shape id、回跳）。目标文件已存在（如外部件动画版）会拒绝覆盖，`--force` 或 `--out` 另存。
4. **目检**：COM 逐页导出（`tools/shot_assets.py` 或 PowerPoint 导出）看溢出、压图、断行。
5. **页标回注＋重渲 docx**：同后处理链第 4 步。

---

## 外部 PPT 后处理链（写作课线）

> **写作课线的 .pptx 不再由本仓 `build_ppt.py` 烘焙**（2026-08-03 立）：改由外部平台生成后复制进 `写作课件PPT输出\<年级册>-第N单元-<题目>\`，本仓只做下面这条后处理链。**读书会线不适用**——`读书会课件PPT输出\` 仍由 `build_ppt.py` 正式烘焙（见下方「调用方式」节），**两套口径不得混用**。

所有命令都**从项目根执行**（`(Get-Location).Path` 确认盘符，移动硬盘会变）。

用户的动作是：外部平台出好 PPT → 丢进 `写作课件PPT输出\` **根目录** → 说一句"处理一下"。
接到这句话就跑下面**四步**，别只做动画就收工（页标漏了，老师对着详案找不到讲到第几页）。

> **详案先读，动画在后**（2026-08-06 用户拍板）：外部件是别人按详案做的，不是本仓产物，它漏了环节、改了归类、剧透了答案，本仓一概不知情。分组顺序本来就以详案为准（见第 3 步），不读详案根本排不出顺序——**先读详案、再据详案审查 PPT，最后才动手做动画**。

> 两件**不属于本链**的事：**打包**交付时另跑 `laojohn-writing-package`，由用户决定时机；**逐页讲稿写作课线已停产**（2026-08-03，`写作课件讲稿输出\` 目录已撤），不要再产。

### 第 1 步 · 认领归位

```bash
PYTHONUTF8=1 python .claude\skills\laojohn-ppt\scripts\place_pptx.py --dry-run   # 先看计划
PYTHONUTF8=1 python .claude\skills\laojohn-ppt\scripts\place_pptx.py             # 再执行
```

把根目录的散件按文件名认领到课次，移进 `写作课件PPT输出\<年级册>-第N单元-<题目>\`，定名为 `<年级册>-第N单元-<题目>-课件PPT.pptx`（2026-08-26 改；旧的 `<题目>-全课.pptx` 已作废）。

- **散在根目录的件打包收不到**（`package_writing.py` 只 glob 课次子目录），这一步不能跳。
- 认领不唯一时脚本会列候选**让你选，绝不猜**——照它给的清单问用户。
- 脚本会报告子目录里已有的其它 pptx：**作废的旧烘焙件要删**，否则打包一并收走（踩过）。

### 第 1.5 步 · 压缩媒体（**仅当入库件 >5MB 时跑**，2026-09-02 立、同日降级）

```bash
PYTHONUTF8=1 python .claude\skills\laojohn-ppt\scripts\shrink_pptx_media.py "<课次目录>\<课次>-课件PPT.pptx" --dry-run
PYTHONUTF8=1 python .claude\skills\laojohn-ppt\scripts\shrink_pptx_media.py "<同上>.pptx"
```

**什么时候需要**：常态下**用不上**——按交付边界（见本节末），仓内只存「审核过＋注入动画」的版本，体积约 1.5MB/份，无需压缩。只有当外部交来的已是人工嵌图后的大件（13~22MB）时才跑，判据＝**单份 >5MB**。

**为什么要有这道工序**：外部件每份 13~22MB，一轮 7 份就是 125.5MB；而 `写作课件PPT输出\` 是入库的（CLAUDE.md §8）、**git 只进不出**，每轮外部重做都再叠一次。08-20 定「PPT 入库」时 pptx 都是 `build_ppt.py` 烘焙的、每份约 1MB，那条决策的前提对外部件已不成立。2026-09-02 体检：`.git` 已 689MB、远程 549MB，GitHub 软建议 1GB——两三轮即触线。

病因不是分辨率（图普遍 ≤1.4MP、长边不超 2000px，投屏够用），是 **AI 插画用无损 PNG 承载**：pptx 约 **89% 是 `ppt/media/`**，且 zip 层压不动。量化 256 色后实测 **125.5MB → 42.6MB（34%）**，透明通道保留。

- **只换 `ppt/media/*.png` 的字节**，不碰任何 XML／rels／SVG。**验收判据＝压缩前后页数/形状数/动画行为数/点击触发数逐项相等**（本次 7 份全等）。
- **画质须目检**：量化对水彩/插画类几乎无损（实测 2.00MB→0.36MB，质感、发丝、渐变、透明均保留），但**首次对一批新风格的图仍要抽一张看**。
- ⚠ **只压新入库的件，不要去压已在远程历史里的旧件**——旧版收不回，压了反而再叠一个版本。
- ⚠ **判重能力补偿**：压后仓内 pptx 与外部件不再字节一致，「重复投放三项比对」的 media md5 项会失效。脚本默认写 sidecar `<pptx>-origin.json` 存原件指纹（整体 md5 + 各 media md5 + 原始字节数），**以后判重与它比，别与仓内 pptx 比**；别加 `--no-sidecar`。
- 压缩后须重跑第 2 步 audit（本次复跑 7 份仍 0 条待办）。

**读书会线不适用**——`读书会课件PPT输出\` 由 `build_ppt.py` 烘焙、体积正常，不接此工序。
### 第 2 步 · 读详案，据详案审查 PPT

**先把详案整篇读完**（`写作课详案输出\<年级册>-第N单元-<题目>-写作课详案.md`），再动任何脚本。

```bash
PYTHONUTF8=1 python .claude\skills\laojohn-ppt\scripts\audit_against_plan.py "<课次目录>\<课次>-课件PPT.pptx"
```

脚本按 **pptx 所在课次目录名**拼详案路径（不搜索，故不受弯引号/全角字符影响），跑五类机检、把结论写进工作单的 `audit` 字段。**这道闸门是硬的**：没跑过、或详案在审查后改过（md5 对不上），第 3 步的 `animate_pptx.py` 直接拒绝注入。

- 机检只管五类：**时长加总**（各环节是否 45、子环节加总是否超标称）、**重复环节**（`[XXX（约 N 分钟）` 前缀重复）、**屏幕指令多于正文页**、**示范文逐字**、**引号**。表格差异列在 `notes` 里供人判——PPT 常有意压缩表头与说明列，那不算错。
- **闸门守的是「做过」，不守「全绿」**：`issues` 非空照样放行（多半要另行改详案），但交付前要有说法。
- ⚠ **人仍须整篇读详案**：机器给不出教学顺序，也判不出「这页归类写反了」。机检全过不等于审查完成。
- ⚠ **别用自己拼的关键词搜详案**：题目常含弯引号（`小小“动物园”`）、全角下划线（`我和＿＿过一天`），`Get-ChildItem -Filter "*小小动物园*"` 一个都搜不到，会误判成「详案不存在」——2026-08-06 踩过，8 页分组按版面猜错、全部返工。要自己找就直接列 `写作课详案输出\` 全目录肉眼认；脚本已不受此影响。
- 详案确实缺失时才降级：`inspect_pptx.py` 与 `animate_pptx.py` 都加 `--no-lesson-plan` 显式放行，交付时须讲明分组顺序无据可依，并告知用户第 4 步做不了。

读完对着 PPT 过两遍，**审查结论先报给用户，不要闷头改 PPT**（本链不改 PPT 内容）：

**① 完整性**——列一张「详案环节 → 页码」对照表，逐条查：
- 每个环节、每处 `[投屏…]` 指令有没有对应页；**详案要求投屏而 PPT 没有的，就是缺页**（实测：《小小“动物园”》详案要投「熊、蜜蜂、猴子、老虎、猪」第一屏，PPT 只在页脚用一句话带过）。
- 详案里的表格（对照表、骨架表、旁批表、评价标准表）是否都有页承载，行数对不对。
- 配图占位是不是真图：`blipFill` 为 False 的大形状是空色块，图并没有贴上。
- 各环节标称时长加总是否仍等于 45+45。
- **稿纸页**：三套外部人工终稿都在自由写作说明页后插一页稿纸页（学生用第 2 页截图＋红色计时徽标）。仓内直出件自带、每次用 `tools/grab_worksheet.py` 现截；外部件由人工终稿补，本链不加。
- **习作讲评页不该出现**（2026-09-26 用户定：详案「附：习作讲评指导环节」一律不进课件 PPT）。外部件带了讲评页，报用户删除；删页会让后面的页码前移，页标回注以删后的页序为准。

**② 正确性**——逐页把 PPT 文字和详案对应段落比对：
- 示范文、表格数据、评价标准这类**成篇成表的内容必须逐字一致**；差异要指名到行。
- 归类/判断类文字（如旁批表「这一句在做什么」）两边说法是否打架。
- 详案自身的矛盾也在这一步暴露（实测：详案表头写「①先填」、正文却说「第二栏」；示范表某格违反自己定的「五个字以内」；**第 2 课时环节三整段重复写了两遍**）。这类**多半是 PPT 对、详案错**，报给用户去改详案，别反过来改 PPT。
- ASCII 直引号计一次数（外部平台常带，与全仓弯引号铁律冲突）。

**③ 顺序**——把详案师话顺序标注到每页的形状上，直接产出第 3 步的 `PLAN`。这一步的产出就是分组依据，所以审查和分组是同一件事，不能拆开做。

机检抓不到的两类，靠人：完整性里的「详案要投屏而 PPT 没做」（脚本只在指令数多于正文页数时判定必然缺页），以及正确性里的归类打架。

### 第 3 步 · 注入点击动画

```bash
PYTHONUTF8=1 python .claude\skills\laojohn-ppt\scripts\inspect_pptx.py "<课次目录>\<课次>-课件PPT.pptx"   # ① 勘查出建议分组
#                                     ② 用 regroup_anim.py 重建分组（见下，不能省）
PYTHONUTF8=1 python .claude\skills\laojohn-ppt\scripts\animate_pptx.py "<同上>.pptx" "<同上>-anim.json" --in-place   # ③ 注入
```

**第 ② 步不能省，且不要手改 JSON**：分组是教学判断，几何启发式只给得出「组的构成」，给不出教学顺序，实测还会跨条目错位（把上一条的正文和下一条的序号绑成一组）。用 `regroup_anim.py` 按版式模式重建——

```python
import sys; sys.path.insert(0, r"<项目根>\.claude\skills\laojohn-ppt\scripts")
from regroup_anim import dump_shapes, run, audit
dump_shapes(PPTX, [4, 8])            # 先打印 位置索引→shape_id→几何→文字 对照表
PLAN = {3: ("row", 0.5),             # 自上而下逐条：单列条目页、表格逐行页
        5: ("grid", 0.8),            # 先分行、行内再分格：2×2 网格页
        7: ("col", None),            # 自左向右逐栏：并列卡片页
        4: ("explicit", [[7,8],[17],[10,11]])}   # 顺序与版面不一致时显式写位置索引
run(PPTX, PLAN); audit(PPTX)         # 落盘 -anim.json，并自检装饰认领
```

**分组顺序一律以详案为准**（2026-08-04 用户拍板）：点击次序跟着详案师话走，哪怕屏幕上要从底部跳回顶部。老师照详案讲、点到哪句屏上亮哪句，不会脱节。实测有四页存在详案顺序与版面上下位置打架，全部以详案为准。

据详案排序时的四类典型改动（2026-08-06《小小“动物园”》实测，26 页里 8 页需要改）：

1. **页脚金句条不一定最后点。** 外部件把「用动物比喻人，你们早就会了」这类句子固定放页脚，详案里它常出现在中段——照详案插进中间那一击。
2. **判语类文字要延后到讨论之后。** 对比页的卡片标题（「写满了猫」「写的是奶奶」）是讨论结论，先出就剧透；改成先出两段正文，讨论完再和旁批一起揭晓。同理，选项条上预印的答案（「→更像熊猫」）要按详案追问顺序挪到最后一击。
3. **详案写「整篇出示」「留在屏幕上自主阅读」的，就别逐条揭示**——该页整页 `skip`，或前几条逐条、剩下的一次出齐（实测示范文页 skip，旁批表带读前四行、后四行一次给）。
4. **详案写了填写顺序的表，按格揭示而不是按行**（对照表「先填第②格，再问什么动物，才写下动物」——三行同序，12 击）。

**四个坑**（细节与实测现象见 `regroup_anim.py` 文件头）：

1. **工作单里的数字是 `shape_id`，不是 `slide.shapes` 的位置索引。** 两套编号数值范围重叠（实测 `shape_id = 索引 + 2`），第 ③ 步那道「id 是否存在于本页」的校验拦不住——曾整份 19 页全部绑错、标题被当正文藏起来，靠投屏才发现。`animate_pptx.py` 现已加防呆（页顶元素或整页背景被卷入即报错退出，`--allow-header` 可放行）。
2. 装饰的吸附目标只能是文字形状，否则一串小圆点会互相吸引、全聚到第一组。
3. 判断「装饰罩住了谁」必须二维；判断「是不是页顶装饰」看它整体是否在正文之上，别拿固定线卡（大底纹的 top 常压着标题区）。
4. 认领小装饰用边缘间隙，不是中心距离（圆点会被同行一个高大标签抢走）。

- 动画 XML **一律走 `helpers.add_click_reveal`**，禁在新脚本里复制那段时间树——`helpers.py` 是两条线共用、有 bug 史的横切层，必须单一源。
- 注入前先清该页已有 `<p:timing>`，**幂等可反复跑**；已带动画的件也能重新分组再注入。
- `inspect_pptx.py` **拒绝覆盖已审查/已校正的工作单**（`--overwrite` 才放行）——重跑一次就冲掉几十页排好的分组。存量件想补审查直接跑 `audit_against_plan.py`，它会自己补 `lesson_plan` 字段，不必重跑 inspect。
- 自动标 skip：封面、末页、课时分隔页（眉标纯数字或含 END）、可分组数不足、整页只有一张表。其余靠人判断。
- **pptx 被 PowerPoint/WPS 打开时注入会 PermissionError**，让用户关掉再跑。

### 第 4 步 · 详案页标回注（委托 `laojohn-ppt-draft`）

```bash
# ① 从 pptx 生成待填骨架（page/kicker/title 自动填好，anchor 留空）
PYTHONUTF8=1 python .claude\skills\laojohn-ppt-draft\scripts\pageback_annotate.py "<详案.md>" \
    --from-pptx "<同上>.pptx" -o "写作课件中间稿输出\<课次>\<题目>-页标映射.json"
# ② 人工填每条 anchor＝详案里该页取材处的行首原文
# ③ 回注（幂等：先清旧标再重插）
PYTHONUTF8=1 python .claude\skills\laojohn-ppt-draft\scripts\pageback_annotate.py "<详案.md>" "<映射.json>"
```

- **锚点按「翻页发生在开始讲这段时」定位**——锚到那句师话，别等到表格或引文才标。
- 映射表存 `写作课件中间稿输出\<课次>\`（该目录入库；PPT 输出目录整个被 gitignore，放那儿会丢）。人工填的锚点是判断成果，值得留存复用。
- 锚点不存在/不唯一/留空/页序倒挂，脚本一律**报错退出且不改详案**——照报错改映射表即可。
- **回注改动了详案 `.md`，必须重渲 docx——两步，缺一不可**：

```bash
PYTHONUTF8=1 python .claude\skills\laojohn-lesson-plan\assets\md_to_laojohn_docx.py "<详案.md>" \
    --header-left "老约翰·同步习作" --header-right "写清楚·写生动·有章法"
PYTHONUTF8=1 python .claude\skills\laojohn-lesson-plan\assets\style_front_page.py "<详案.md>" "<详案.docx>"
```
漏传页眉参数会**静默回落**成读书会页眉。**漏跑第二步 `style_front_page.py` 同样静默**——首页掉回共享引擎的朴素版式（提纲表变成表头整行铺底的原始 md 表格，而非定稿的左侧栏铺底单表），2026-08-03 已因此返工一次。docx 被 WPS 占用会报 PermissionError，请用户关掉再跑。

- **该课若有配图版（详案正文含 `【图位:…】`），配图版必须一并重出**——老师实际用的是配图版（教材图全在那儿），只重渲无图版等于把没页标的那份交出去。2026-08-04 已漏过一次：页标回注后只重渲无图版，续写故事的配图版停在两天前、不含 21 个页标。**必须在上面两步之后跑，且必须传 `--base-docx`**：

```bash
PYTHONUTF8=1 python .claude\skills\laojohn-lesson-plan\assets\insert_images_docx.py "<详案.md>" \
    --profile writing --base-docx "<详案.docx>"
```

不传 `--base-docx` 的话，回插件会自己现调引擎另出一份基础 docx——那份**没跑 `style_front_page.py`**，首页会掉回朴素版式。传入刚重渲好的无图版，配图版才同时继承页标与首页版式。取图目录由 `writing` 档的 `name_from: stem` 按详案文件名解析到 `写作课教材插图\<年级册>-第N单元-<题目>\`，不用给 `--images-dir`。

### 交付边界（2026-09-02 用户拍板）

**本仓工序止于第 4 步。** 之后人工会在外部平台嵌入插图、优化文字，那一版才是**给老师的终稿**——它**不回本仓**，也不进 `写作课件PPT输出\`。

- `写作课件PPT输出\` 里存的是**本仓工序的产出**（审核过＋注入动画），不是终稿。定位是「本仓这道工序做完的样子」，供双机协作与追溯。
- **终稿的归档在外部平台/固定目录**（用户已确认会一直留着），本仓不再存副本——这也是体积账的根本解法：终稿嵌了大插画 13~22MB，动画注入版只有约 1.5MB。
- **打包不收 PPT**：`laojohn-writing-package` 已于同日去掉「投屏PPT」分类，否则交付包里会混进没有插图的半成品。老师的 PPT 由人工从外部终稿直接提供。
- **页标以本仓这一版的页码为准**（用户口径：人工基本不做页码增删，个别情况个别处理），所以第 4 步照常在本仓版上做，不必等终稿。

⚠ 若某次外部交来的已经是人工嵌图后的终稿（不是初稿），那这一份就无法只存动画注入版——先跑第 1.5 步压缩再入库，并在该课次记忆文件注明属特例。

### 可选第 5 步 · 本仓添图（2026-09-25 六上五试点定稿）

用户要求「本仓直接把插图嵌进课件」时才做，不做时照旧交外部人工嵌图。**成品另存桌面，不回 `写作课件PPT输出\`**（守上面的交付边界）；仓内动画注入版原样不动，页数不变，所以页标照旧有效。风格样板与用户定稿过程见记忆 `ppt-illustration-style-reference-0925`，动手前必读。

1. **出图**（课件配图工具，通道 gpt-image）：
   - 场景插图按原流程走，`run_lesson.py` 或网页端，出到 `页目/`。
   - **要立在底带或页边上的人物，一律单独生成透明底版**：`python 课件配图工具/scripts/gen_cutouts.py 课件项目/<项目>.json`，清单写在项目 JSON 的 `抠图件` 里，产出放在 `抠图/`。**不要拿页目图后期抠**，页目图自带水彩底晕，残边抠不干净，用户三次点名。
   - 吉祥物是项目里的一个角色件（本课主角男孩招手的半身像）。
2. **写版式清单**：`课件配图工具/课件产出/<项目>/ppt配图版式.json`，逐页写 op（swap／add／geom／band／font／fill），全局写 theme、tip_icon、mascot。格式见工具头注释。
3. **生成**：`python .claude/skills/laojohn-ppt/tools/illustrate_pptx.py <版式清单.json>`。原图位用 swap 在原形状里换图，shape id 不变，动画绑定保留；新加的图不进动画。
4. **核验**：用 PowerPoint COM 导出全部页截图逐页看；再按上面「收尾核验」的思路查 shape id 有没有重复、anim.json 里的 id 是否都还在、有没有新增的动画回跳。
5. **补齐终稿**（2026-09-26 六上五 v9 沉淀）：`tools/finalize_external.py`，对配图终稿与仓内动画版各跑一次——
   - `--worksheet-after N --student-html 写作配套输出/<课次>/<课次>-学生用.html`：自由写作说明页（第 N 页）后插稿纸页；
   - `--drop-match 习作讲评`：删讲评页；
   - `--text-from 润色稿.pptx`：外部另有文字润色版时，按 shape_id 逐框换文字（几何、动画不动）；
   - `--zh-cn`：外部件 run 一律标 en-US，PowerPoint 按英文断行、标点落行首——改 zh-CN，页题放不下的顺带加宽。
   仓内动画版旁的 `-anim.json` 会按新页序自动重排；之后重跑 `audit_against_plan.py`、页标回注、重渲详案 docx。

版式口径（用户逐条定过；**仓内直出件以母版 `assets/writing-master/framework.md` §四之二 为准，与下面同一口径**，本节只多出后期改外部件时才用的操作）：
- 以图为主重排，不在原版式里找空地塞小图：正文让出右栏，人物落在浅色底带的底边或页面底边上，页脚提示句收窄，给人物让位。
- 底带看页面加，不是每页都要：让人物有落脚处、页面显得饱满时才加；物件图（比如碎杯子）不需要。
- 卡片页的小插画要收进卡片，贴在卡片右下角、略微探出卡边，不能孤零零放在卡片外面。
- **分节页、结尾页一律不加图**（全线适用，工具的 `is_section` 会自动跳过）。封面照常放人物。
- 表格页、三栏已排满的页不放主图；**整篇示范文页要配图**（末尾几段收窄、人物立右下，v8 P18）；判断题页的配图不能画出答案。
- 全课统一：页题条按本课主题从五色里选一色（粉 `FCE7EA`／浅绿 `E6F2E1`／浅蓝灰 `E3E9F2`／浅桃 `FDEBD9`／浅黄 `FFF3D6`，六上五外部件用的是浅蓝灰）、分节页纯色、每页页题条右端立吉祥物、页脚提示句前加手指图标（`品牌资产/图标/手指点击.png`）、卡片表头上彩色。**2026-09-26 用户定这三样（主题色页题条、吉祥物、手指图标）为默认**，仓内直出同一口径，写在母版 `assets/writing-master/framework.md`「本仓增补」。
- ⚠ 收尾**不调** `normalize_paragraphs`：外部件的多 pPr 段落会被它改坏，改完 PowerPoint 就打不开。
- 输出文件如果正在 WPS／PowerPoint 里打开，保存会 PermissionError，就改成新版本号另存。
### 收尾核验

- **动画绑定必须从 pptx 的时间树反查实证**，别只信注入器那句「回读核验通过」——它只对得上「点击条数」，对不上「绑到了哪个形状」，坑 1 就是这么漏过去的：

```python
import json, re, zipfile
from pptx import Presentation
from pptx.util import Emu
prs, z = Presentation(P), zipfile.ZipFile(P)
doc = json.load(open(P.replace(".pptx", "-anim.json"), encoding="utf-8"))
for pg, sl in enumerate(prs.slides, 1):
    v = doc["slides"].get(str(pg))
    xml = z.read(f"ppt/slides/slide{pg}.xml").decode("utf-8", "ignore")
    tgt = {int(x) for x in re.findall(r'spTgt spid="(\d+)"', xml)}
    if not v or v.get("skip"):
        assert not xml.count('nodeType="clickEffect"'), f"P{pg} 应跳过却有动画"
        continue
    assert xml.count('nodeType="clickEffect"') == len(v["groups"])
    assert tgt == {s for g in v["groups"] for s in g}
    assert not [sh for sh in sl.shapes if sh.shape_id in tgt      # 标题不得被卷入
                and sh.has_text_frame and sh.text_frame.text.strip()
                and Emu(sh.top).inches < Emu(prs.slide_height).inches * 0.22]
```

- **pptx 在页标回注之后又改动过的话，须比对页数与每页眉标·标题**——变了就重跑第 4 步。改动只涉及页内文字/顺序（本次三份都是）则页标仍然有效，不必重来；一旦增删页，页标会整体错位且同样是静默的。比对时注意两类假阳性：眉标形如 `附 · 习作讲评` 的，页标只留后半段；标题里 ` · ` 两侧的空格在页标中会被压掉。

```python
import io, re
from pptx import Presentation
from pptx.util import Emu
norm = lambda s: re.sub(r"\s+", "", s or "").replace("·", "")
tags = {int(m.group(1)): m.group(2) for m in
        re.finditer(r"〖PPT 第(\d+)页 · ([^〗]*)〗", io.open(MD, encoding="utf-8").read())}
for pg, sl in enumerate(Presentation(PPTX).slides, 1):
    if pg not in tags:
        continue
    tops = sorted([s for s in sl.shapes if s.has_text_frame and s.text_frame.text.strip()],
                  key=lambda s: Emu(s.top).inches)
    got = norm("".join(t.text_frame.text for t in tops[:2]))
    want = norm(tags[pg]).replace("课时分隔", "")
    assert not want or want in got or got in want, f"P{pg} 页标与 pptx 对不上"
```

- 课次目录里 pptx 只剩该留的那份（作废件已删）
- 详案页标数 == pptx 页数 − 封面 − END，页码连续
- 详案 docx 已重渲
- **投屏前须核 ASCII 直引号**：外部平台产的文本常带直引号，与全仓弯引号铁律冲突（样本 25 页里 92 处）。这属于内容问题，动画工具不修——发现了告诉用户。

## 文件加载策略（先读这里）

| 文件 | 何时读 |
|---|---|
| 本 SKILL.md | 每次 |
| `references/page-contract.md`（中间稿契约唯一源：元信息/分页头/页型枚举/7 字段/`{{}}` 填空答案/`参考：` 答案上屏/v8 版式选择器/实景观察/自动封面与 END/完整示例） | 编译前核对输入、或诊断"页型未识别"时 |
| `references/visual-variants.md`（视觉规范与差异化渲染唯一源：v6.1 关键词高亮与环节标题自适应/v7 逐条点击动画规则/故障排查表） | 关心视觉行为、调动画、排查渲染问题时 |
| `references/architecture.md`（profile 分层架构：共享层/呈现层、页型×profile 归属、写作专属页型清单） | 改代码、加页型、判断某页型归哪个 profile 时 |
| `laojohn-ppt-draft/references/writing-mode.md` §2/§2.5/§2.6/§2.7 | 写作页型**字段写法**唯一源（本 skill 不复制） |

## 契约速览（细则见 page-contract.md）

- 一份中间稿 = 一节课的 PPT。分页头 `## P14 | 页型:原文齐读`；**P01 固定封面、正文从 P02 起**，每课时独立编号；**PPT 页面上不标页码**。
- 页型**按 profile 裁决**：读书会（缺省）6 种（封面/环节标题/引导问题/原文齐读/要点小结/填空表格）；写作课（元信息 `文体：写作` 触发）自成一套（共用 3 种 + 情境任务/写法讲解/活动指令/示范文/双栏对照/写作任务/实景观察）。写错 profile 会因查不到 renderer 报错。
- 字段 7 个：眉标（**不写课型**）/标题/副标题/正文/要点/表格/配图建议。要点行下 `参考：答案` → 红字点击上屏；填空表格 `{{答案}}` → 底表留空、逐格点击揭示；引导问题页 2–4 条配图建议 → 2×2 四图网格。
- 封面与 END 页自动注入；逐条点击动画默认开启（`--no-anim` 关闭）。

## 调用方式

### 固定输出目录

> ⚠ 路径与本机环境约定见根 `CLAUDE.md` §1：执行前用 `(Get-Location).Path` 确认实际项目根目录，下文 `<项目根目录>` 代表该路径，禁止硬编码盘符。

**所有投屏课件 PPT 按课型线保存到（与中间稿目录同线对应）：**

```
读书会（文体缺省） → <项目根目录>\读书会课件PPT输出\<书名>\
写作课（文体：写作） → <项目根目录>\写作课件PPT输出\<年级册>-第N单元-<题目>\
宣讲（文体：宣讲）   → <项目根目录>\写作课相关宣传文件\<宣讲件名>\
                       （对外宣传件，与招生海报同族；该目录整个 gitignore，
                         中间稿与成品同住一夹，改字重烘靠 build_ppt.py）
```

例：`<项目根目录>\读书会课件PPT输出\俗世奇人\俗世奇人-导读课.pptx`、`<项目根目录>\写作课件PPT输出\三上-第六单元-这儿真美\这儿真美-写作指导课.pptx`

```bash
cd .claude/skills/laojohn-ppt/scripts
python build_ppt.py --input "<项目根目录>\读书会课件中间稿输出\<书名>\<书名>-<课型>-中间稿.md" --output "<项目根目录>\读书会课件PPT输出\<书名>\<书名>-<课型>.pptx"
```

可选参数：`--course` 覆盖课时／`--book` 覆盖书名／`--logo`、`--banner` 自定义素材（默认 `../assets/logo/logo-red.png`、`../assets/decorations/cover-banner.jpg`）／`--no-anim` 关闭点击动画（默认开启）。

执行后终端输出"配图占位清单"——交给老师即知哪些页需手动贴图。

## 不做的事

- 不生成内容，不改写文案
- 不内嵌字体（保证 .pptx 体积小、跨平台兼容）
- 不自动配图（始终给老师占位框）
- 不导出 PDF（让 PowerPoint/WPS 自行导出）

## 文件结构

```
.claude/skills/laojohn-ppt/
├── SKILL.md
├── references/
│   ├── page-contract.md    中间稿契约唯一源
│   ├── visual-variants.md  视觉规范/动画/故障排查唯一源
│   └── architecture.md     profile 分层架构（CLAUDE.md §3 接缝原则的细则）
├── scripts/
│   ├── build_ppt.py        入口 CLI（按元信息 文体 选 profile）
│   ├── parser.py           中间稿解析（共享·课型无关）
│   ├── layouts_common.py   公共元素 + 参数化封面基函数 + END（两 profile 共用）
│   ├── layouts_reading.py  读书会 6 页型渲染 RENDERERS_READING
│   ├── layouts_writing.py  写作课页型渲染 RENDERERS_WRITING
│   ├── theme.py            字号/颜色/坐标常量（读书会默认）
│   ├── theme_writing.py    写作课视觉变体常量
│   ├── helpers.py          文本框/占位框/表格工具 + 点击动画注入（共享·课型无关）
│   │                       ——外部 PPT 后处理链（写作课线）——
│   ├── place_pptx.py       第1步 认领归位：根目录散件 → 课次子目录 + 规范命名
│   ├── plan_link.py        详案绑定单一源：按课次目录名定位详案 + 抽结构摘要（禁各脚本自写匹配）
│   ├── audit_against_plan.py 第2步 机检五类，结论写入工作单 audit（不跑则第3步拒绝注入）
│   ├── inspect_pptx.py     第3步① 勘查形状、按卡片聚簇出「建议」分组工作单
│   ├── regroup_anim.py     第3步② 按版式模式重建分组＋装饰认领（四个坑写在文件头）
│   └── animate_pptx.py     第3步③ 按工作单注入点击动画（import helpers，幂等，回读核验＋绑定防呆＋审查闸门）
├── assets/    logo/ · reference-ppt/ · decorations/
├── examples/  mini-test.md（最小端到端样例）+ mini-test.pptx
└── tools/     parse_slide.py（开发期 XML 侦察）；pptx_text_edit.py；shot_assets.py；illustrate_pptx.py（可选第 5 步·本仓添图）；finalize_external.py（添图后补稿纸页／删讲评／换润色文字／中文断行）；html_to_pptx.py＋writing_deck_kit.py＋direct_build.py＋grab_worksheet.py（仓内直出）
```

---

## 宣讲件不走后处理链（2026-08-24）

`文体：宣讲` 的件由 `build_ppt.py` **本地烘焙**，动画在渲染时由 renderer 直接注入。
外部 PPT 那条后处理链（归位 → 读详案审查 → 动画 → 页标回注）**对它完全不适用**：
`plan_link.py` 按课次目录名硬拼详案路径，宣讲件没有详案，会直接抛 `PlanNotFound`。

⚠ 别把宣讲件丢进 `写作课件PPT输出\`——那会触发归位脚本，认领到一个不存在的课次上。
