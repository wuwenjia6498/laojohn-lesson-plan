---
name: correction-tool-upload-hold-0907
description: 批改工具上线闸门(0907装)：标准包须人工确认(confirm_pack.py)才被 build_deploy 打包，未确认不上线、已在线的随下次部署下线；五上三《故事新编》/三下六/五下八/旧题缩写故事按此不确认即不上；10包判据已对齐现行详案、对照表在核对清单目录，待用户逐包确认后部署
metadata:
  type: project
---

2026-09-07 用户先拍板三条暂停（五上三《故事新编》详案要重写、不抽包不上传；三下六《身边那些有特点的人》与五下八《漫画的启示》先不上传），随后拍板把它做成机制：**人工核对确认过的包才上线，不确认就不上，已在线的同样适用**。

## 机制（同日已装，三处代码 + 三份文档）

- `作文批改工具/confirm_pack.py`（新）：`<包名|lesson_id> --by 确认人` 确认 / `--revoke` 撤销 / `--list` 看状态。确认前置门两条：核对清单凭据存在（同 validate E26）、validate 对该包 0 FAIL。写回 `source.verified_by_human/verified_by/verified_on[/verified_note]` 与核对清单第 3 行表头。
- `web/build_deploy.py`：只打包 `verified_by_human is True` 的包；0 个已确认拒出空包；写盘前列「本次新上线/下线/有改动/不变」并要求敲 y（`--dry-run` 只看，`--yes` 跳过提问但**不跳过闸门**，无 `--allow-unverified`）。stdin 非终端时不提问直接拒写——`input()` 在 agent 宿主里收不到 EOF 会挂死（实测踩过）。
- `validate_packs.py` E26 扩：true 必须带 verified_by 与 verified_on；E27 WARN 撤销残留。
- 服务端/前端不动：线上 `_packs.json` 只剩已确认包，徽章恒「判据已核」；本地 `load_packs()` 仍读全目录。

## ⚠ 现状与部署前必做

- 15 包全未确认，此时跑 build_deploy 会被「0 个包已确认」挡住——**预期行为**。
- **（同日下午已修）10 包判据/锚句已按现行详案对齐，validate 只剩《缩写故事》3 FAIL；对照表＝`标准包核对清单/_判据对齐记录-20260907.md`，末节是逐包确认命令，确认由用户自己跑。**《我的家人》包内「爷爷」改回「姥爷」（用户核最新教材）。以下是修前记录：基线 validate 有 26 FAIL、落在 11 个包（C15/C16「查无此句」：包 08-21 抽的，详案 0831/0901 大改后判据不再逐字一致）；只有《续写故事》《这儿真美》《身边那些有特点的人》《漫画的启示》4 包 0 FAIL。confirm 会拒绝有 FAIL 的包，所以**要留在线上的 12 课得先把判据改到与详案一致，再逐包 confirm**，然后 build_deploy（看到三课下线）→ `vercel --prod`。
- 「先不上传」的三课（含旧题 `5a-u3-suoxie-gushi`）不需要任何动作：不确认即下线。
- 线上课次接口要口令（Vercel 环境变量 `LJ_ACCESS_CODE`，本地没有），线上清单只能凭打包件推断。

**Why:** 此前 `verified_by_human` 四个消费点全不阻断，`build_deploy` 全量 glob，「先不上传」没有机器保障——改稿纸列数顺手一部署就把目录里全部包带上线。
**How to apply:** 动部署前跑 `confirm_pack.py --list`；给新课抽完包不等于上线，确认才上。关联 [[writing-correction-tool-0818]] [[writing-correction-tool-vercel-deploy-0824]] [[gushi-xinbian-5a-unit-move-0828]]
