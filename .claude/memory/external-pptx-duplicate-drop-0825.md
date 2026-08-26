---
name: external-pptx-duplicate-drop-0825
description: 外部 PPT 再次丢进根目录时先做三项比对判重，别直接归位——place_pptx 会静默覆盖已处理件，动画与引号修正一并丢失
metadata:
  type: feedback
---

用户把外部件丢进 `写作课件PPT输出\` 根目录说「处理一下」时，**先判断这是不是已处理课次的重复导出**，再决定跑不跑第 1 步归位。

2026-08-25 实测：`五三.pptx`（外部原始导出）与课次目录里已跑完全链的 `缩写故事-全课.pptx` **完全同源**——570 个形状的 id/类型/位置/尺寸逐一相同、281 个文本块逐字相同，25 张图内容哈希相同；唯一差别是已处理件多了 98 处点击动画、且 88 处 ASCII 直引号已改弯。直接跑 `place_pptx.py` 会按同一课次认领并覆盖，**动画和引号修正全部丢失且不报警**。

**Why:** 归位脚本按文件名认领课次，判不出「目录里那份是你自己加工过的成品」。外部平台重新导出一次极容易（用户换机器、忘了已处理、协作对方又导了一遍），而覆盖的代价是整条链第 2–4 步白跑。

**How to apply:** 课次目录里已有成品（2026-08-26 起叫 `<年级册>-第N单元-<题目>-课件PPT.pptx`，此前叫 `<题目>-全课.pptx`）时，归位前跑三项比对——
1. 文本块：逐形状 `text_frame.text` 拉平成列表做 `difflib`，看差异是否只是引号；
2. 媒体：`ppt/media/*` 逐个 md5 取集合比内容（文件数可能差一个空的 `ppt/media/` 目录条目，不算差异）；
3. 几何：`(页,shape_id,type,left,top,width,height)` 全等 → 同源铁证。

三项全等即判为重复件，**不归位**，问用户删不删（散件留根目录会在下次归位时被误认领，且 `package_writing.py` 只 glob 课次子目录、打包收不到）。三项有实质差异才是真修订版，按正常四步链重跑，且第 3 步动画注入前须重跑 `audit_against_plan.py`（页标回注改过详案，md5 必然对不上闸门）。

判重顺手可做的收尾核验：动画时间树反查 + 页标↔pptx 逐页比对（两段脚本在 `laojohn-ppt/SKILL.md`「收尾核验」节），能一次性确认已处理件是否完好。

相关：[[writing-ppt-external-plus-animation]] · [[writing-ppt-review-against-detail-first]] · [[manhua-laoshi-5a-ppt-chain-state]]
