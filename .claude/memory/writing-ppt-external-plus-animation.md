---
name: writing-ppt-external-plus-animation
description: 写作课PPT改外部平台生成+本仓只做动画后处理；讲稿页序改跟外部pptx；读书会线不变
metadata: 
  node_type: memory
  type: project
  originSessionId: 67b5d254-8b99-4d07-baa9-4b11975aacb5
  modified: 2026-08-06T02:27:45.006Z
---

**⚠ 2026-09-26 起重写详案的课次改走仓内直出（见 [[writing-ppt-direct-build-pilot-0926]]），本条的外部件链只管存量课次。**

**2026-08-03 用户告知的流程变更（仅写作课线）**：写作课 .pptx **不再由本仓 `build_ppt.py` 烘焙**，改由外部平台（PptxGenJS 驱动的工具）生成，复制进 `写作课件PPT输出\<年级册>-第N单元-<题目>\` 后，本仓只做**动画处理**。读书会线完全不变，仍走 `laojohn-ppt` 编译。

**Why:** 这个变更此前没有任何文档记录，直接造成三处脱节——打包脚本收的是作废的本仓烘焙件而非老师真正要用的那份；逐页讲稿按中间稿 19+10 页写、外部件却是两节合一的 25 页，页序 1:1 契约断裂；本仓「每节课独立 PPT 不合并」的既定契约与外部件相冲突。

**How to apply:**
- **入口话术＝「<题目> 的 PPT 放好了，处理一下」**（用户把外部件丢进 `写作课件PPT输出\` **根目录**即可，不必自己归位）。触发 `laojohn-ppt`，其 SKILL.md 就是**四步**运行手册：① `place_pptx.py` 认领归位 → ② **读详案、据详案审查 PPT**（2026-08-06 用户拍板新增的硬序，见 [[writing-ppt-review-against-detail-first]]）→ ③ 动画 → ④ 页标回注 + 重渲 docx。**接到这句话别只做动画就收工**。**打包不在链内**（用户另行触发 `laojohn-writing-package`）。
- **写作课线的逐页讲稿已停产（0803 用户拍板，不要再产）**：`写作课件讲稿输出\` 目录已删、存量 6 个文件已删、`package_writing.py` 的讲稿档已撤、`lecture-notes.md` 已标注只适用读书会线。**读书会线照旧**产讲稿。`pptx_outline.py` 保留但改用途＝校正动画分组／备课时看每页屏上有什么。
- **动画三段式**（脚本在 `laojohn-ppt/scripts/`）：`inspect_pptx.py` 勘查 → **`regroup_anim.py` 重建分组** → `animate_pptx.py` 注入。中间那步不能省、也不要手改 JSON：几何启发式只给「组的构成」，给不出教学顺序，还会跨条目错位（把上一条的正文与下一条的序号绑成一组）。**工作单里的数字是 shape_id 不是位置索引**，填错会静默绑歪整份——详见 [[ppt-anim-groups-are-shape-ids]]。
- **分组顺序一律以详案为准**（2026-08-04 用户拍板）：跟着详案师话走，哪怕屏上要从底部跳回顶部。三份实测有四页详案顺序与版面上下位置打架，全部以详案为准。
- 动画 XML 只走 `helpers.add_click_reveal`（presetID=10 淡入 + onNext），**禁复制那段时间树**——它是两条线共用的横切层。注入前先清 `<p:timing>`，故幂等可反复跑。
- **讲稿页序事实源改为外部 pptx**：先跑 `laojohn-ppt-draft/scripts/pptx_outline.py` 抽页序骨架再逐页写；页型标签位改用 pptx 眉标；节奏行必须写明本页点击次数与推进顺序（老师照讲稿点屏幕）。中间稿降级为外部平台的生成依据，不再定页序。
- **命名**：~~两节合一用 `<题目>-全课.pptx`~~ **⚠ 2026-08-26 改为 `<年级册>-第N单元-<题目>-课件PPT.pptx`**（与合一与否无关；讲稿已停产）。见 [[writing-line-naming-flattened-0826]]。放进课次子目录才会被 `package_writing.py` 收（它 glob `写作课件PPT输出/{unit}/*`，根目录散件收不到），且要清掉作废的旧烘焙件否则一起被收走。
- **详案页标回注**走 `laojohn-ppt-draft/scripts/pageback_annotate.py`（`--from-pptx` 出骨架 → 人工填 anchor → 回注，幂等）。本线页码取外部 pptx 物理页序、**全课连续**（不按课时重编），页标第二段没有页型、改放 pptx 眉标 —— `〖PPT 第3页 · 创设情境 · 先玩个游戏——猜猜他是谁〗`；课时分隔页要标（锚在 `## 第N课时` 前、第二段写「课时分隔」），封面与 END 不标；眉标自带 ` · ` 要压掉否则页标撑成四段。**锚点按「翻页发生在开始讲这段时」定位**——锚到那句师话，别等到表格或引文。人工填好的映射表存 `写作课件中间稿输出\<课次>\<题目>-页标映射.json`（PPT 输出目录整个被 gitignore，放那儿会丢）。口径见 `detail-pageback-annotation.md`「写作课线适配」节。回注后必须重渲详案 docx。
- **ASCII 直引号是本线通病，且查法有陷阱**：外部件把直引号存成 `&quot;` 实体，直接对 `<a:t>` 文本 `count('"')` 会查出 0 处、误判为干净（0804 三份都这么漏报过）；用 python-pptx 读 `run.text` 才看得见（三份实测 66/66/52 处）。修法＝按文本框逐个开闭配对换成 `“”`，只换字符不动文案。

首个样本＝《猜猜他是谁》（三上第一单元），25 页 74 次点击，见 [[writing-line-filename-unit-segment]]、[[xuxie-gushi-textbook-image-rewrite]] 同线其余约定。
