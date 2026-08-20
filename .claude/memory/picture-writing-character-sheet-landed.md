---
name: picture-writing-character-sheet-landed
description: 角色册已落盘 assets/角色册/角色设定.md（根目录 0728 那份自此作废）；定妆图六张定稿、小试拍板走手工
metadata: 
  node_type: memory
  type: project
  originSessionId: 0f222829-a94a-48a5-9b79-125409a3a258
  modified: 2026-07-29T08:39:53.201Z
---

2026-07-29 定妆图收口轮的三件跨会话状态：

**① 角色册的事实源已迁移。** 唯一源＝`.claude/skills/laojohn-picture-writing/assets/角色册/角色设定.md`。
根目录 `角色册设定与四格题材序列-0728.md` 的**第一部分自此作废**（它是落盘前的稿，未含九条回写），
但**第二部分（12 组四格题材序列）仍有效**、尚未填进 `references/topic-registry.md`。
→ 改角色设定改 assets 那份；引用根目录那份的第一部分即为引错。

**② 定妆图第一批 6 张全部人工定稿，但图未入库。** `assets/角色册/` 目录已建、只有 md。
六张图与 `_临时_角色定妆/` 的删除都等人工放图。迭代路径与四条提示词纪律见
`第三轮决策日志-0728.md` 末尾的「定妆图出图轮（2026-07-29）」区——**第二批 4 张（二年级档）开工前必读**。

**③ 小试（拿妆-01 跑真实场景主图、量头身比）已拍板走手工，不走脚本。**
根因不是脚本做不到，而是**两条参考图指令常量各废一半**：
`_ANCHOR_REF_INSTR` 明说「不要沿用参考图中的角色」→ 测不到角色一致性；
`_STYLE_REF_INSTR` 明令沿用「人物造型比例」→ 等于主动把定妆图的 2.5 头身灌进去，
「会不会传染」测不出中性结论。**技术上能不改代码指定后者**（造壳详案含 `主-01` 占位＋`主-02` 真规格，
妆-01 拷进 `图位/主-01.png`，跑 `--only 主-02` 即走组图非首格分支），**但指定了也不解决问题**。
缺口由第四轮待办 `_CHAR_REF_INSTR`（沿用画风与角色身份、比例另按文字给）填。
判据：场景图基线 3.3~3.6 头身，仍在区间＝2.5 没传染，可铺 55 张。

相关：[[picture-writing-image-style-lock]]、[[picture-writing-global-style-tokens]]、
[[picture-writing-imgspec-writing-lessons]]
