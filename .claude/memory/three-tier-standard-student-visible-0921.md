---
name: three-tier-standard-student-visible-0921
description: 三档标准改学生可见——〔三档标准·教师掌握（不必读给学生）〕括注以后一律不写，skill 规则已同步
metadata:
  type: feedback
---

2026-09-21 用户对五上五详案定的**常设口径**：`〔三档标准·教师掌握（供教师判断用，不必读给学生）〕` 这个括注**以后都去掉**，标签写成 `〔三档标准〕` 即可——**学生可以知晓判档依据，方便他照着改自己的稿**。

**Why**：判档依据藏着，学生改稿时没有靶子；写作课的三档本来就是「怎么算写好了」，念给学生听比老师自己攥着有用。与 `lesson-structure.md` §三⑥.6 早就承认的「学生可见自评表不属教师掌握组」同向，这次把**评价档位整类**移出教师掌握家族。

**How to apply**：
- 已改的事实源两处：`laojohn-writing-lesson/references/lesson-structure.md`（§三 括号家族五类清单、`评价标准/评分档位` 表行、⑥ 开头加「评价档位不在本组」）、`references/checklist.md` `参考：` 标签纪律行。⑥ 其余条款仍管 `〔修改符号说明·教师掌握〕` 这类真不念给学生的块。
- `tone_gate.py` 的「教师掌握块悬空与括注」检查**只在出现 `〔…教师掌握…〕` 时才触发**，标签去掉后自然不报，脚本不必改。
- **存量 45 份详案未回溯**——用户说的是「以后」，只在改到某篇时顺手改。

相关：[[writing-lesson-positive-framing-not-prohibition]]、[[jieshao-shiwu-5a-lesson-state]]
