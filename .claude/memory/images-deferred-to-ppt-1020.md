---
name: images-deferred-to-ppt-1020
description: 野性的呼唤/萨哈拉建档时无原图、档案写「本书无插图」；用户放的图未整理，定到做PPT时再补图单挑图
metadata:
  node_type: memory
  type: project
  originSessionId: f1fa50ff-e53c-488f-b98f-4e92feabf9b4
  modified: 2026-10-20T10:31:05.867Z
---

2026-10-20 用户定：《野性的呼唤》《特别的女生萨哈拉》两本，建档时还没放原图，档案里分别写着「本书无插图，故档案不设第十节」「未建原书插图目录」，详案中 `【图位】` 为 0。用户后来把图放进了 `读书会原书插图\<书名>\`（分别是 57 个、25 个文件，未整理），里面混着其他书的封面、背景资料图、作者照等。**现在不补，等做 PPT 时再挑图。**

**Why:** 档案的事实与原文不受影响，详案也可以当无图版用。受影响的只有插图链路，而 PPT 链本来就支持「新放进来的图先补图单再配页」（见 `laojohn-ppt-draft/references/image-suggestion.md`）。

**How to apply:** 做这两本 PPT 时：① 别信档案里的「无插图」，先查图目录；② 先分拣（非插图移入 `_非插图素材\`），逐张目视、对照档案写 `_图单.md` 与 `_清洗记录.json`，并问用户这些图出自哪个版本；③ 这一步必须在 AI 自动生图之前完成——手绘编号按原书插图来选；④ 补完后，把档案的「无插图」句改为 `## 十、原书插图` 指针节。详案不必补图位。同类口径：[[reading-ppt-auto-ai-images-1014]]、[[book-profile-read-images-during-profiling]]。
