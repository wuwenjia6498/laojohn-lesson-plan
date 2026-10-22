---
name: video-assets-location-1020
description: 视频素材 2026-10-21 起在 my-Workspace _assets 总库（D:\老约翰视频素材 已并入）；品牌片、AI 讲解员宣传片输出都在 my-Workspace 04-projects\video\（后者靠 PROMO_VIDEO_ROOT）
metadata:
  type: reference
---

**2026-10-21 起素材以 my-Workspace `_assets\` 总库为准**：现场视频、阅读场景、宣传设计稿、产品讲解视频已并入，`D:\老约翰视频素材\` 不再往里放。总库只放常用素材，顶层按 01–07 分大类（存档在 `D:\老约翰素材归档\`）（课堂实拍照片在 `01-课堂实拍照片\` 下），宣传片脚本里的 `assets:` 路径要带这层前缀。权威版本：my-Workspace `_assets\素材总览.md`。

原桌面 `临时\做宣传片\` 2026-10-20 拆分后删除：

- **素材** → `D:\老约翰视频素材\`（不入 git，只放素材，不放工程）
  - 现场视频（10 段课堂实拍）、阅读场景（18 张）
  - 可以单独发的重要版块内容（KT 板、展架、网页图）
  - 产品说明 PDF（43 页；「课标 450 万字」口径有误，以 my-Workspace 权威引用卡片 145 万为准）
  - L2/L3/L4 三套样课包、2024 年四段讲解视频
- **1 分钟品牌片 v13 工程**（huashu-motion，原 `_motion\laojohn-brand-promo`）→ `D:\my-Workspace\04-projects\video\brand-video\brand60\`
  - 帧缓存与旧版成片已清，只留 out\ 下 v13 和配乐对比-B
  - my-Workspace 全局忽略 png/jpg/mp4/wav，git 只收代码和文档
  - 预览：`om studio D:\my-Workspace\04-projects\video\brand-video\brand60`

- **AI 讲解员宣传片输出**（2026-10-20 起）：laojohn-promo-video 不再写本仓 `宣传短视频输出\`（已删），改写 my-Workspace `04-projects\video\<线目录>\ai-promo\<课次>\`（读书会 dushuhui-video／写作课 writing-video／看图写话 picturewriting-video），视频根由 `promo.config.json` 的 `PROMO_VIDEO_ROOT` 指定，没配即报错；脚本源文件在 my-Workspace 入库。本机同一配置里的 `PROMO_ASSETS_ROOT` 已从失效的 E 盘改到 `D:\my-Workspace\_assets`

相关：[[promo-parent-facing-no-teacher-side-1020]]
