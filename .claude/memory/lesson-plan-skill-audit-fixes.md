---
name: lesson-plan-skill-audit-fixes
description: "2026-07-06 读书会SKILL全套通读审计:A/B类已修(含两项用户拍板口径),C冗余/D架构类待办清单"
metadata: 
  node_type: memory
  type: project
  originSessionId: 1eb01051-adf9-4ee8-b034-b33cd844853b
---

2026-07-06 对 laojohn-lesson-plan 全套 + laojohn-detail-review 做通读审计，A 类（误删恢复）与 B 类（文件间矛盾）已全部修复；C（冗余）/ D（架构）类**待用户拍板后处理**。

**用户已拍板的两个口径（恒久）：**
- **答案标签统一 `参考:`**——L5–L6 的 `明确:`/`参考资料:` 为旧样本称法、已弃用（引擎只识别 `参考:`）；已改 style-and-format 三处 + examples-usage 防串味注（L5/L6 旧范例 txt 里仍有 明确:，不模仿）。
- **课时数等级默认钉死**（L1/L2=2、L3–L6=4）——档案「建议课时数」仅作提醒信号，与等级不符时停下问用户、不自行改结构；已改 checklist + book-profile FACTS-ONLY 模板字段说明。

**已修的其他 B 类：**
- 复盘形态命名全仓统一为 rubric 口径：**形态A=无生成上下文（A·强隔离=fresh子agent / A·手动=新会话），形态B=同会话顺接降级封存**。改了 detail-review SKILL、lesson-plan SKILL、writing-lesson SKILL 三处旧文（旧文把新会话叫形态B）。
- 阅读版 review-rubric 头部编号修正（原"第7.5道工序/第8步导出"→7自检/8复盘/9导出）+ 两版 rubric 顶部改为冷审执行方视角。
- detail-review「无争议直改清单」按课型分列——**阅读详案导读课尾布置"7天读完全书"是必须动作非错误**（原混排清单会诱导冷审误删）。
- lesson-plan SKILL「改文字」保护清单：去已废弃 `【PPT换页-PXX】`、补 ppt-draft 回注的 `〖PPT第N页…〗`。
- style-and-format「典型切分」指路修正（数据在 source-docs/样本证据汇总.md，非 grade-structure）。

**A 类已修：** lesson-templates.md 导读课六条环节菜单曾被本轮编辑误删（git HEAD 取回逐字插回）+「思辨讨论:——」标点残迹清理。

**C 类已修（2026-07-06 同日）：** C10 写作技法解锁口=CLAUDE.md §6 唯一源（SKILL/style-and-format 压成摘要+指针）；C11 同日连排=grade-structure 唯一源（SKILL 第5步压缩）；C12 装载量/密度**判据数字唯一源=checklist**（生成方必读侧；师话轮次对标汉修81/俗世76 已并入 checklist 密度条①，rubric 维一两处改为引用 checklist、不复述数字——冷审 agent 需按 rubric 指路开 checklist 取阈值）；C13 弯引号码位细则=课案Markdown约定规范 §7 唯一源；C14 docx 封面工程细节（DrawingML/1/4圆/logo幽灵/COM验证等）从 style-and-format 整段移入规范末尾「附:引擎自动版式」（按需读，生成流程不读）；C15 落地清单两处悬空引用已修（L5-L6-example-criteria.md/OPEN-QUESTIONS.md 均不存在，改指 examples-usage 并补列漏记的 reading-strategies/review-rubric）、已删未跟踪遗留物 laojohn-lesson-plan.zip（6-25 旧打包快照，内容全是仓库旧副本）与 assets/__pycache__。

**D 类已修（2026-07-06 同日，审计全部闭环）：** D16 **不搬家、写清分工**——checklist 的判断类条目是历次拍板加入的第一道自查，与 rubric 冷审构成**有意的纵深防御**；已在 checklist 头部加「两类条目·分工声明」（合规项+质量预检项；两道有意重叠不得互删；判据数字唯一源=checklist、查法详述以 rubric 为准）、rubric 头部加对应段（第二道不因自查过而略过任何一维）。D17 三类文本判定新增**第 0 条「用户定调优先」覆写出口**（lesson-templates 判定规则+SKILL 2b+checklist 三处，附玛丽阿姨实证）。D18 提纲第 3 项改为「只列本书实选的 3–7 项,不是照抄该等级策略全集」。
