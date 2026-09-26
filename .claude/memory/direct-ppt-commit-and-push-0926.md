---
name: direct-ppt-commit-and-push-0926
description: 仓内直出的写作课 PPT 完成即入库并 git push 到 GitHub，给同事看（用户长期授权，不必再问）
metadata:
  type: feedback
---

2026-09-26 用户定：以后仓内直出的 PPT 入库并上传 GitHub，这样另一位同事才能看得到。

**Why:** 双人协作只有 git 一条通道（见 [[two-person-sync-0820]]）；直出件用到的图在 `课件配图工具/课件产出/**` 不入库，同事那边重渲不出来，只能靠入库的 pptx 看到成品。

**How to apply:** 直出一课走完 direct_build → 目检 → 页标回注 → 重渲 docx 后，按 `direct_build.py` 打出的入库清单（pptx、-anim.json、课件构建脚本、详案 md、页标映射 json）提交并 `git push`，属长期授权，不必逐次再问。推前确认提交身份是本人（CLAUDE.md §9）；>5MB 先跑 shrink_pptx_media。外部件的人工嵌图终稿仍不回仓，两条口径别混。相关：[[writing-ppt-direct-build-pilot-0926]]。
