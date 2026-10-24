---
name: image-gen-default-1280-medium-1024
description: 全仓生图缺省改为长边1280+medium(Gemini 1K)；野性的呼唤三页对比投屏看不出差别、真实账单单张$0.29→约$0.06；大图用环境变量临时覆盖
metadata:
  type: project
---

2026-10-24 用户定：**以后所有生图（课件、海报、看图写话、宣传片讲解员等）默认长边 1280＋medium**。

**Why**：野性的呼唤课件 65 张图原按 2048×1536 high。量下来投屏上最宽只显示约 800 像素（中位 797、抠图约 500）。三页对比（场景/狼群/抠图）按投屏尺寸看三档没有差别，放大局部 medium 笔触略粗、不糊。
**真实账单（AiHubMix 后台，按美元扣）**：gpt-image-2 文字输入 $5/1M、图像输入 $8/1M、图像输出 $30/1M。2048 high 输出 8,892 tok＝$0.267；输入随挂载参考图数变，每多一张约 1,450 tok≈$0.012（1/2/3 张＝约 1,350/2,820/4,280 tok），单张合计 $0.276–0.300。全书约 73 次≈$21≈¥150。⚠ 用户给的「¥」价格表数值等于美元价，别当人民币用。1280 medium 输出 1,395 tok＝$0.042，加输入单张约 $0.05–0.08，只省到 1/4–1/5；降档后参考图输入占单张 20–45%，再省就看少挂参考图（未试）。
**How to apply**：缺省在共享件 `课件配图工具/scripts/imgclient.py`（`_ratio_px` 按 `IMAGE_LONG_SIDE` 缺省 1280 算 gpt-image／豆包像素；gpt-image `OPENAI_IMAGE_QUALITY` 缺省 medium；Gemini `GEMINI_IMAGE_SIZE` 缺省 1K）；看图写话自带 `generate_images.py` DEFAULTS 与 imggen.config(.example).json 同步改为 1K／1280x864。**本地配置只放密钥和地址、不写尺寸**（同日定）：模板 `课件配图工具/.env.example`、`imggen.config.example.json` 与本机两份 gitignored 文件都删了尺寸行，否则本地值会盖住代码缺省；`setup_check.py` 第5项会对写死的尺寸/质量报提醒；`docs/协作同步说明.md` 第四节写了同事机器手动删行（每台一次）。确需大图（印刷）时临时设 `IMAGE_LONG_SIDE=2048` / `OPENAI_IMAGE_QUALITY=high` / `GEMINI_IMAGE_SIZE=2K`，不改缺省。三通道均已实测出图：gpt-image 1280x960、豆包 1280x960、Gemini 1K＝1200x896。存量图不重出。gpt-image 无 seed，对比只能比质感不能比同一构图。
