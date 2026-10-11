---
name: reading-ppt-v9-media-size-1011
description: 读书会v9 PPT 曾每份20–50MB；1011 已在 helpers 嵌图处根治（大PNG缩长边1600+量化），别再事后跑 shrink
metadata:
  type: project
---

2026-10-11《稻草人》四课 pptx 合计 135MB（导读课 51MB），用户问为什么这么大，随后拍板「根治」。

**病因**：AI 抠图以 1536×2048 RGBA 无损 PNG 原样嵌入，每张 4–6MB，占体积九成；投屏上最多显示到约 1000px 高。神笔马良、汉修先生等 v9 课件同病（40MB 级）。

**根治（现行）**：`laojohn-ppt/scripts/helpers.py` 的 `_embed_source()`——`add_picture_fit`／`add_image_cover`／`add_image_or_skip` 嵌图前，**>1.5MB 的 PNG** 缩长边到 1600、量化 256 色（带透明走 FASTOCTREE）；JPG、小 PNG（logo／图标／截图）原样。版面坐标与 crop 仍按原图算，所以结构不变。阈值是模块常量 `EMBED_PNG_MIN_BYTES`／`EMBED_MAX_SIDE`。

**回归法与结果**：同一批中间稿改前改后各烘一次，逐页逐形状比（类型、位置、尺寸、文字、裁切到 3 位小数）——稻草人四课＋神笔马良＋汉修先生（v9）＋洞（旧样式）＋写作课＋宣讲九份全部相同；后三份媒体字节 md5 也全同。v9 降到原来的 1/4–1/7（稻草人导读课 51→9.9MB），1080p 导出目视无色带、透明边完好。

**How to apply:** 读书会 PPT 照常 `build_ppt.py` 烘焙即可，**不必再事后跑 shrink**。`shrink_pptx_media.py --max-side` 仍留给外部件链路用。稻草人已按新代码重烘。**大头儿子、神笔马良（用户点名，1011）没有重烘、而是对现存成品做事后瘦身**：`shrink_pptx_media.py --max-side 1600 --min-bytes 1500000 --no-sidecar`（与 helpers 同规则），四份 148→31MB、结构逐形状相同。不重烘的原因：用现行引擎重烘这两本，文字框位置高度与形状数都和 10-08/09 的成品不同（引擎此后改过），等于连版式一起换。其余旧书（汉修先生等）用户定先不动。相关：[[reading-ppt-v9-human-optimized-1006]]
