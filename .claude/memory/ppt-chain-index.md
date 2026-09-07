---
name: ppt-chain-index
description: 写作课外部 PPT 后处理链的六条实现细节索引（原挤在 MEMORY.md 一行，0907 下沉）
metadata:
  type: project
---

写作课 PPT 链＝**归位 → 读详案审查 → 注入动画 → 详案页标回注**（口径唯一源＝`laojohn-ppt/SKILL.md`）。
六条踩过的实现细节，按遇到顺序：

- [[ppt-delivery-boundary-0902]] — ⚠ **交付边界：本仓工序止于动画注入，人工嵌图后的终稿不回本仓**。
  打包不收 PPT；压缩降级为「仅单份 >5MB 时跑」；仓内约 1.5MB 而终稿 13~22MB，
  ⚠ 下一课次须先确认收到的是初稿不是终稿。
- [[writing-ppt-review-against-detail-first]] — ⚠ **先读详案再审查再动画**（0806 硬序，已装机器闸门）。
  机检全过 ≠ 审查完成；审查照出的多是详案自己的错，**PPT 对详案错时报用户改详案，不许倒过来改 PPT**。
- [[writing-ppt-external-plus-animation]] — 外部平台生成 + 本仓只做动画（0803 立线）。
- [[ppt-anim-groups-are-shape-ids]] — 动画工作单填 **shape_id，不是位置索引**（0804）。
- [[manhua-laoshi-5a-ppt-chain-state]] — 手工加的动画会被注入器**静默清掉**（0825）。
- [[external-pptx-duplicate-drop-0825]] — 重复投放先做三项比对判重（0825）。

相关：[[writing-line-naming-flattened-0826]]（pptx 与 anim.json 必须同批改名，否则防覆盖闸门静默失效）。
