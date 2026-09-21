---
name: bijian-liuchu-6a-ppt-broken-0921
description: 仓内六上四《笔尖流出的故事》课件 pptx PowerPoint 拒开（自 0918 产出起），17 份里的孤例，已排除所有已知坑
metadata:
  type: project
---

**仓内 `写作课件PPT输出\u516d上-第四单元-笔尖流出的故事\...-课件PPT.pptx 打不开**，
报 `PowerPoint could not open the file.`（HRESULT -2147467259 通用失败，不说原因）。
2026-09-21 做备课视频出图时撞上。

**范围：孤例。** 仓内 17 份写作课 pptx 逐份 COM 打开测过，**16 份能开，只这 1 份不能**。
所以不是后处理链的系统性 bug。

**时间：从产出就是坏的。** git 里只有一个版本（0ecaee4 后处理链走完那次），
bdebb15（术语改名）没动过这个文件（字节数一模一样）。
**当时没人用 PowerPoint 开过它验收**——动画注入走 python-pptx，注入成功≠PowerPoint 能开。

## 已排除（别重查）

| 查了什么 | 结果 |
|---|---|
| zip 完整性、178 条目 | 正常 |
| 42 张 media 图 PIL 逐张 verify | 全可解 |
| 所有 xml/rels 的 lxml 解析 | 全合法 |
| rels 引用完整性（rId 双向对账） | 0 问题 |
| **已知三坑**（重复 shape id／timing 空容器／endParaRPr 不在段末） | **全部阴性** |
| 缺 `p:bldLst`（三上一有 14 个 bldP、六上四一个没有） | 补上仍不开，**不是根因** |
| 剔掉全部 25 页 timing | 仍不开，**与动画无关** |
| python-pptx 读入再存（洗一遍） | 仍不开 |
| 逐页拆开单测 | **30 页里 26 页坏**；能开的四页是 P1 封面、P2／P23 课时分隔、P30 THE END——都是结构页 |

指向：坏在教学页 spTree 的内容层，而且是 PowerPoint 严格校验、lxml 与 python-pptx 都不报的那一类。

## 连带口径

- **外部终稿不在仓内**（CLAUDE.md §8：人工嵌图终稿不回本仓），所以仓内这份坏不影响已交付给加盟商的件——
  但它是本仓唯一的备份，且备课视频的画面源靠它。
- 排查手法沉淀：**判是不是环境问题，先拿 PowerShell 的 `New-Object -ComObject PowerPoint.Application` 直开**。
  PowerShell 能开、python 不能开 → 是 pywin32 的 gen_py 缓存坏了（删 `%LOCALAPPDATA%\Temp\gen_py\`）；
  **两边都不能开 → 是文件本身坏**。这次是后者。
