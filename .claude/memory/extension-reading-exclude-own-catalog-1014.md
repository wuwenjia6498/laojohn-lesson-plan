---
name: extension-reading-exclude-own-catalog-1014
description: 下游物料「拓展阅读」对读书会课表书的处理：低年级书只能写成重读口吻，同级及以上不推；课表外须适龄
metadata:
  type: feedback
---

拓展阅读建议（阅读指南等）里，读书会课表里的书不当新书推。

**Why:** 1014《稻草人》(L3) 指南先推《快乐王子》（课表在五年级，三年级读不透），换成《去年的树》又撞上二年级书目，《安徒生童话》也是三年级课表书——常来的孩子已读过，当新书推等于白占一条。用户随后补充：低年级读过的书可以换个说法，写成「你可能在X年级读过《…》，可以再读一遍……」。

**How to apply:** 课表清单＝`laojohn-pipeline/references/reading-club-catalog.md`（1014 用户给的 26.4.15 版，165 本，从 62MB xlsx 抽出、xlsx 不入库）＋`读书会书籍档案\` 全部书名（稻草人等在建书不在课表里）。低于本书年级的课表书→重读口吻；同级及以上→不推；课表外→正常推、须适龄。课表更新时让用户给新表重抽覆盖。规则唯一源在 reading-guide SKILL.md 拓展阅读节。与 [[reading-guide-extension-concrete-titles]] 同栏。
