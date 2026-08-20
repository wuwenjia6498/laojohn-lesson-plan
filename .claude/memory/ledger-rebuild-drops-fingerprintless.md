---
name: ledger-rebuild-drops-fingerprintless
description: 重建反同质化台账前必须先查哪几篇详案的指纹块被删过，否则那几行会被静默抹掉
metadata:
  type: project
---

2026-08-19 生成五上《缩写故事》定稿时，按工作流第 7 步扫 `写作课详案输出\*.md` 重建 `variation-ledger.md`，结果登记表从 14 行掉到 12 行——四上《推荐一个好地方》《小小“动物园”》两篇的指纹块**不在文件里**（是 2026-08-04 用户逐句改稿时连同投屏提示一起顺手删掉的，`prose-style-benchmark.md` §三已记这一现象，但没人把指纹补回去），重建脚本按"文件里现在写着什么"覆盖，两行就没了。已从旧表逐字回写两篇文件尾的指纹块，再重建，14 行齐。

**Why:** 台账的设计前提是"指纹块＝唯一真相来源、只重建不追加"；一旦成稿的指纹被删，这条链就反过来吃掉历史记录，而且**不报错**——下次查重时那两篇的场景/载体/热身全部隐身，会误判成"没人用过"。

**How to apply:** 重建前先 `grep -L VARIATION-FINGERPRINT 写作课详案输出/*.md` 数一遍缺指纹的篇；缺的先从旧表回写进文件尾再重建。重建脚本可复用 scratchpad 里的 `rebuild_ledger.py`（按册级＋中文单元号排序，`|` 转全角）。同一条对看图写话线的同类台账也成立。相关：[[writing-lesson-fingerprint-fields-revised]]、[[writing-lesson-antihomogenization-upgrade]]。
