---
name: writing-line-audit-0913-remaining
description: 0913 写作线 skill 通读审计：第一至三档已改，第四档（去重与来历下沉）缓到有新数据点再做，清单在此，做完即删
metadata: 
  node_type: memory
  type: project
  originSessionId: 6b9d4836-0599-40e4-a517-9438414435ed
  modified: 2026-09-12T16:15:47.986Z
---

2026-09-13 对 `laojohn-writing-lesson` 全 skill 通读审计（三个 fresh agent 分片：交叉一致性／整体冗余断链／机检实跑），发现分四档。**第一档 5 条与第二档 5 条当日已改**（口径以冷审 rubric 为准：投屏不预告答案三来源／减法三问补复述型·覆盖型·⑦器具≤2 件／旁批表最见功夫两句必入表、表末说明出路已删／brief §一.4 与 workflow·SKILL 改按避让卡／model-essay:3 单一源声明改写）。**第三档（残留词／断链／计数／essay_audit 三处中档／tone_gate 与 detail-review 措辞）0913 同日清完**：essay_audit 已改为注释不删行、片段比对扩到「、；」与并列引语、核 0 格与无引块打 WARN、锚点句运行时取自 model-essay §四之三；tone_gate 清单解析为空打 WARN；pools 池 6/7 锚行旁加解析警告；detail-review 补「跨维查项同属 Pass A 必做」。**第四档未动，建议等两三篇新稿跑过换靶流程后再做：**

## 第四档 · 去重与来历下沉（多为存量）
- technique-levels.md 无 history 文件、五处保留来历；SKILL.md 11 处日期（:44 整段 0804 改制理由）；rubric 九头部一整段试审来历
- 「教学指令正向表述」五文件五处完整判据；弯引号铁律 SKILL 内三遍；附录标题与三节名逐字复述四处；提纲表末两行体例五处；L5–L6 定起点段五处
- generation-brief:9「只索引不复制」与 §一.1/.2/.5/.7/.8 完整判据不符
- 存量数据点（0913 新版 essay_audit 实跑 24 篇）：③ 原报 11 篇共 21 格不是子串，**0913 晚查实其中约半数是脚本缺陷**——`frags_in_order` 剥了格内引号却没剥示范文侧的引号，凡含“…”引语的格永远判不成子串；已修（示范文侧同剥），复跑后剩 7 篇 11 格（猜猜他是谁 3／我来编童话 2／漫画的启示 2／小小动物园·我和过一天·推荐一个好地方·故事新编各 1），仍为存量待人判，② 疑似改写 9 处，均为存量稿待人判、不回改；两篇无 `>` 引块（写观察日记／二十年后的家乡）不合体例；《漫画老师》_优化版示范文 697 字、《故事新编》771 字，均超 L5 上限；《故事新编》旁批表行 290 一格不是子串（待人判）

**How to apply**：做第四档时每条判据先点唯一源（正向表述→lesson-structure §三 8；附录标题→title-naming §四；提纲表两行→lesson-structure §四 5–6；定起点→workflow ⑥；弯引号→SKILL 输出形态），其余缩成一句指针；rubric 改过须派冷审跑一篇验收；改 pools/lesson-structure 前先看 tone_gate 四锚。做完本文件即删并撤 MEMORY 未决行。相关：[[zhang-zuqing-on-writing-line-0912]]、[[model-essay-rules-supplement-0912]]。
