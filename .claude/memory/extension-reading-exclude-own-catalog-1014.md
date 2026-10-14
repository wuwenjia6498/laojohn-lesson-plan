---
name: extension-reading-exclude-own-catalog-1014
description: 下游物料「拓展阅读」不推荐读书会自己课表里的书，且须适龄；仓内无完整课表
metadata:
  node_type: memory
  type: feedback
  originSessionId: edafd4c2-5916-4722-bedc-fbee972a08f4
  modified: 2026-10-14T08:36:00.839Z
---

拓展阅读建议（阅读指南等）不得推荐读书会已有书目，且须按本书等级适龄。

**Why:** 1014《稻草人》(L3) 指南先推《快乐王子》(仓内定 L5，三年级读不透)，换成《去年的树》又撞上 L2 书目，《安徒生童话》也在课表里——常来的孩子已读过，等于白推。

**How to apply:** 排除源＝`读书会书籍档案\` 全部书名＋lesson-plan `references\examples\` 样本书＋已知在册《去年的树》《安徒生童话》；仓内没有完整课表，交付时提醒用户核对，拿到课表后存进仓并更新本条。规则已写进 reading-guide SKILL.md 拓展阅读节。与 [[reading-guide-extension-concrete-titles]] 同栏。
