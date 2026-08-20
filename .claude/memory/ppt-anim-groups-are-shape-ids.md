---
name: ppt-anim-groups-are-shape-ids
description: 外部PPT动画工作单里的数字是shape_id不是位置索引（差2且范围重叠、静默绑错整份）；已加防呆+regroup_anim.py，改动画分组前必读
metadata: 
  node_type: memory
  type: project
  originSessionId: 3ae2a4fc-0098-4a6b-8861-5f94d1ff824a
  modified: 2026-08-04T16:48:26.979Z
---

`laojohn-ppt` 外部 PPT 后处理链第 2 步的分组工作单（`<题目>-anim.json`）里，`groups` 填的是 **OOXML `shape_id`**，不是形状在 `slide.shapes` 里的位置索引。2026-08-04 三份写作课 PPT 加动画时按位置索引写，整份 19 页全部错位。

**Why:** 实测 `shape_id = 位置索引 + 2`，两套编号数值范围完全重叠，`animate_pptx.py` 原有的「该 id 是否存在于本页」校验一路放行；它落盘后的「回读核验通过」只对得上**点击条数**，对不上**绑到了哪个形状**。结果是标题被当正文藏起来、末尾金句一开机就亮着，三份都注入完、汇报完，靠用户投屏截图才发现。

**How to apply:** 动画分组相关的活，一律走 `.claude/skills/laojohn-ppt/scripts/regroup_anim.py`（用版式模式 row/col/grid/explicit 重建，落盘前自动转 shape_id；四个踩过的坑写在文件头）。不要手改 JSON、不要自己写脚本填 groups。`animate_pptx.py` 已加防呆：页顶元素或整页背景被卷入即报错退出（`--allow-header` 放行）。验收必须**从 pptx 时间树反查 `spTgt spid`**，脚本那句「回读核验通过」不足以证明绑对了——核验代码在 `laojohn-ppt/SKILL.md` 的「收尾核验」节。

同批踩到的三个装饰认领坑（圆点互相吸附、二维覆盖判定、边缘间隙而非中心距离）见 [[writing-ppt-external-plus-animation]] 与 `regroup_anim.py` 文件头。
