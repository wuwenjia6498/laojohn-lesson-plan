---
name: skills-audit-fixes-0726
description: 2026-07-26 两写作技能全面审查后的批量修缮与三项用户拍板（组图平级编号/60分钟执行弹性/装置逃生口）
metadata: 
  node_type: memory
  type: project
  originSessionId: fee5a273-f56e-4a1d-80ed-9d7d5a432f6c
  modified: 2026-07-26T15:51:33.376Z
---

2026-07-26 对 picture-writing 与 writing-lesson 做全面审查（两 fork 子代理逐行读＋主会话交叉核验），P1/P2 无争议项已全部修入（21 文件），P0 三项用户拍板：

1. **组图编号＝平级方案**：多图课四格用 `主-01…主-04` 平级编号（**弃 `主-01-1` 三段式**，脚本正则零改动）；规格新增字段 `组序:`（第N格·起因/经过/结果）、`格间变化:`、`状态: 留白（不生图…）`（缺图补全课留白格，`generate_images.py` 见「留白」跳过）；`imgspec_parser.KNOWN_FIELDS` 已收三字段＋`is_blank`/`group_seq` 属性；**组图主-02 起自动带主-01 作图生图参考锁画风与角色**（anchor 固定为首格不漂移）。唯一源＝image-spec §组图。
2. **60 分钟纯口头课＝执行弹性**：详案一律按 45+45 产出，机构可现场压缩至约 60 分钟执行、不另出 60 分钟版详案（SKILL/course-map/lesson-structure 三处已统一，checklist「每节 45」不加豁免）。
3. **装置字段逃生口＝例外＋留痕＋熔断**：默认必须配独立装置；技法确无从当场演仍如实填（无）但须括注原因；同年级连续第 3 个（无）停下请用户定夺（variation-ledger §一/§三查重口径已改，「不得再填」硬门撤销）。

其余已修的高危项（勿重复排查）：写作线附录标题三处半角→全角归一 title-naming、course-map §六旧行名（这一课/对齐统编）重写为课题·课时/核心能力点四行、technique-levels 两处黑板→投屏/学生单、括号家族「四类」→五类（补〔教师示范·〕）、G-102 官方情境补退次选豁免、环节一措辞统一「写下第一组句子」（存量4稿为准）、batch_ngram WHITELIST 删四维标签、六下第六单元写信/策划书两子任务已拆列进 index＋anchors（防误判自拟题）；看图线 terminology 硬替换表移出说话句/心里话（期10 方法名保护）、期20/21 方法名去「句子会变身/把句子写胖」尾（course-map＋ability-ladder 全改）、综合课/回顾课一课一得豁免注、checklist M0→纯口头课、期3 B层指引〈第二期〉→〈第一期〉、一下方法课数 5 非 6、三条冷审结论已落盘（口头必做书面不加码→lesson-structure §5；拟声词属听得见归两想→§5＋model-essay §2；纯口头课换图速看只问不判→§1＋image-spec §三）、文件名与期次副标改「映射规则」表述。

**Why**: 多轮迭代后规则出现「照A走被B判违」型矛盾与双写漂移，集中一轮修净；组图机器链路是二年级多图课（20+ 课次）的地基，生产前必须先建。
**How to apply**: 排多图课时直接按 image-spec §组图平级编号出规格，勿再发明编号；60 分钟与装置字段问题已闭环勿再改口径。未做的遗留：双写收敛（三图位细则 8 处/降压起步 4 处/讲评块 5 处降为指针）风险较高未动；看图线跨篇「拆法措辞不同款」无台账承载。

**追记（同日晚 · AI 腔比重问题闭环）**：用户问 AI 腔约束比重是否过重，量化诊断＝条目占比约 1/4 未失衡、rubric 侧不重，病在机检项混人工清单＋配额软规则无裁决序。已按拍板落地：仓根新建 `tone_gate.py`（--profile picture|writing，[FAIL]/[INFO] 两级；运行时解析 variation-pools 禁止逐字复用清单与 terminology 硬替换表不双写；豁免＝注释区/代码围栏/提纲表 `*` 与 `_`/`> **可压缩预案**：` 式引块批注）；两线 checklist 纯机检条收敛为一条「机检门」（picture 54→51、writing 92→84）；两线 rubric 补密度类裁决序（教学链条完整性＞拟真度＞密度指标，冷审只标不判争议归用户）＋维〇/分流指向脚本。★存量已交付稿的清单/导演腔/行首（历史命中**不回溯**（SKILL：存量不强制回改）——脚本对存量 writing 稿报 1~2 项 FAIL 属预期，验收标准是「无凭空误报」非「存量全绿」。★顺带发现并按引块批注家族豁免了一处规则矛盾：title-naming §3.5 的 `> **可压缩预案**：` 与 checklist E-61 `*` 禁令字面冲突。相关：[[picture-writing-three-image-slots]]、[[picture-writing-cold-review-round-0726]]、[[writing-lesson-fingerprint-fields-revised]]、[[deai-language-rules-solidified]]
