---
name: wild-call-pages-verified-physical-book-1024
description: 《野性的呼唤》详案里的 P0xx 页码已由用户按纸质书核过，不是编造；档案仍写「epub 无固定页码」
metadata:
  node_type: memory
  type: project
  originSessionId: 5f5cc737-f076-4936-b062-8620ff748088
  modified: 2026-10-24T15:54:06.484Z
---

2026-10-24 用户确认：《野性的呼唤》课案详案引文后的 P005、P035-036、P154 等页码**已按纸质书核过，不用改**。

但书籍档案仍写着「流式 epub 无固定页码，下游出现第X页均属编造」（档案第3、32、115、364行），与机读块「页数：154页」自相矛盾——下游 agent 读档案会把详案页码误报成编造（测评卷生成时就报过一次）。

**Why:** 档案的页码声明是建档时的旧口径，纸质书核对发生在后，没回写档案。
**How to apply:** 再遇本书页码疑点不必再问用户；测评卷照 CLAUDE.md 仍只用章节定位。档案那几行是否改写待用户定。相关：[[images-deferred-to-ppt-1020]]
