---
name: writing-lesson-drop-book-club-link
description: "写作课决定不引入读书会书目,book-writing-map 机制整体移除"
metadata: 
  node_type: memory
  type: project
  originSessionId: d04a3056-cdc8-4639-ab26-2da869fa0193
---

2026-06-28 用户拍板:`laojohn-writing-lesson` 写作课**不再引入读书会书目**,`references/book-writing-map.md` 整文件删除,全部触点清干净。

**Why:** 书目连接是单向锦上添花(写作课→读书会书目),却带来悬空引用与维护负担——situation-anchors 标了 3 处「可连接 book-writing-map」,但 map 里实际只有「写作品梗概」一行,推荐一本书/写读后感都扑空,与 map「未匹配=不提书目」及 checklist F 组自相矛盾。砍掉机制比补全更简洁。

**How to apply:** 已清的触点——删 book-writing-map.md;SKILL.md 去掉文件加载表那行 + 「读书会书目引用」工作流条;situation-anchors 三处「可连接」标注移除;checklist 删「F. 读书会连接」组,并把 F→价值观、G→反同质化 重排(原 G/H),同步改全 skill 6 处「X 组」交叉引用(价值观落位→F、反同质化/去自注标签核验→G)。**保留不动**:教材**课文/名篇片段**范例(《海滨小城》等,读写打通、与读书会无关,见 workflow ③ / model-essay §四);technique-levels §34 两 skill 可视化对照里提到的「读书会 skill」。CLAUDE.md 无需改(book-writing-map 是 writing-lesson 自有文件,非 §6 共享依赖)。详见 [[writing-lesson-competitor-borrow-backlog]]。
