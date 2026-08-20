---
name: lesson-plan-per-step-load-audit
description: "用户拍板:详案审核须逐环节做\"装载量双向核查\"(过挤+过松都查)+无学生动作环节排查,已固化进checklist与review-rubric"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0f4105a1-001f-4b9e-bc15-74bbfbd7d392
---

用户指出(2026-07-04,骑鹅详案):导读课多个环节标称时长装不满(两轮快问占10分钟、一段资料+一轮讨论占15分钟),且有环节纯教师独白无学生动作,自测 checklist 与冷审 rubric 都没查出来,只能一处处手工修补——要求以"逐环节动作累加对标称"的颗粒度重新审核整份课案。

**Why:** 旧查项只治"挤"(累加超标称)与"收束类轻环节≥10分钟",漏掉两类:①实做环节累加**明显少于**标称的注水(拿虚胖时长凑60);②≥5分钟环节通篇教师独白、零学生动作(还连带违反"答案不说尽")。骑鹅案实测:导读课 10+15→5+5、松出10分钟回补"先睹为快"到官方口径35分钟;交流2 导入5分钟纯独白、写法赏析连续两段独白,均改"先问学生、老师再归纳"。

**How to apply:** 已固化三处——`lesson-plan/references/checklist.md` 结构组新增两条自检(逐环节装载量双向核查、无学生动作环节排查);`review-rubric.md` 维一"逐环节耗时累加"扩成双向+新增"无学生动作环节排查"查项(冷审依据,detail-review 自动加载)。生成新详案时每环节写完即做动作累加;过松的首选改法是充实学生动作(先问后归纳)而非单纯砍时长,砍出的时间优先回补主体实做环节。关联 [[detail-review-cold-start]] [[review-rubric-single-source-dedup]] [[qie-lvxingji-lesson-plan-state]]。
