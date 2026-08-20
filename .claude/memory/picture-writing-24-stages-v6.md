---
name: picture-writing-24-stages-v6
description: 看图写话 v6 内容层升级（历史：24期七模块口径已被取代，现行见 picture-writing-course-map-v4-0723）；期1已产并跑通生图闭环
metadata: 
  node_type: memory
  type: project
  originSessionId: 3b2a1d4b-0859-4f2c-bd86-97658f155dd9
  modified: 2026-07-27T05:02:15.562Z
---

> ⚠ **口径已过时（2026-07-22）**：「24 期七模块」对外口径已被终稿0722 取代——去模块去期数，改「四学期 × 16 次 = 64 课次」，期号降为内部方法编号。现行口径见 [[picture-writing-course-map-v4-0723]]（v3 也已标历史，勿再跳转）；本条余下内容中生图闭环、占位契约、bug 修复等工程事实仍有效。

2026-07-19：web 端产出 `v6-content-layer` 包，我按《合并指令》做了**只在内容层**的合并。**旧的 20 期制 + `competency-matrix.md` 已作废删除**（取代见 [[picture-writing-20-stages-expansion]]，那条只余历史价值）。

**新结构 = 24 期七模块，接入同步习作六阶总轴**（看图写话占第一阶「说清楚·写完整」一年级、第二阶「写连贯·讲成故事」二年级）：模块0 看图说话(纯口头,2期) / 一 看图写实(6) / 二 看图想象(4) / 三 多图叙事(5) / 四 词句雕琢(4) / 五 真实表达(1) / 六 衔接进阶(2,仅L2)。每期 meta 含 图型/训练点/同步锚点/增量类型(同步·超深·超前)/阶/建议学期。课型双轨（方法课 45×2 / 练习课单节 45）；年级双档 L1·L2 × 课内三层。

**references 新格局**：新增 `curriculum-archive.md`(统编写话官方档案 v2,按册 1A/1B/2A/2B,唯一官方锚点源,v1 已被实物核准证伪作废) + `picture-reading.md`(圈画四步法) + `course-map.md`(24期总地图)；覆盖 ability-ladder/image-spec/checklist/scaffold-cards。**`lesson-structure.md`、`model-essay.md`、`scripts/` 全套是我侧独有的引擎层，web 端没有，合并时原样保留**——web 版 SKILL 把这两个写成「待建/缺失降级」，用户拍板丢弃那句、按「每次必读」写入。

**两处 web 版落后于本地决定、已按用户拍板丢弃**：①上述降级说明；②核心约束里「用胖句子/加料/小侦探等儿童化说法」——与去游戏化红线相反。用户要求不止改核心约束、还要清散落残留，实清出 3 处（ability-ladder ×2「加料/变身」、course-map ×1「胖句子」）。

**期1《会看：图上有什么》已产并跑通完整生图闭环**（首次真调 AiHubMix）：5 图（锚-01 + 例-01～04）全过、0 需人工，锚-01 六项清单一次过，用户已人工确认「只有一个孩子」。

**本轮踩出并已修的两个坑（后续期次会复现，故记）**：
1. **web 端生成侧不写机读占位** `【图位:编号】`，只写叙述式「（出示例-01）」——`insert_images_docx.py` 认不到，回插插 0 张。已把「占位是硬契约 + 装配后跑 imgspec_parser 机检双向零缺口」写进 SKILL 工作流第6步与 checklist。
2. **`insert_images_docx.py` 潜伏 bug 已修**：原用 `search()` 每段只取首个占位、随后清空整段 → 同一行连列的例-03/例-04 被**静默吞掉**且不计 missing。改为 `finditer()` 逐个回插。历史详案占位各占一行故未暴露。

另：web 稿带 3 处「黑板/板书」，违反 [[classroom-no-blackboard]]（该约束此前只固化在 lesson-plan/writing-lesson，看图写话侧没有）。已改为「教室墙面张贴 + 每人一张小卡」，并把这条补进本 SKILL 核心约束 + checklist。

**下一步**：P3 一上批剩余期次 期2/3/4/18/19 尚未生成。
