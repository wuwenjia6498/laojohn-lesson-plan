---
name: office-skills-env-facts-0824
description: 本机办公文件工具链环境事实（0824 实测，0911 从 CLAUDE.md §5 下沉）＋ 官方 docx/pptx/xlsx/pdf skill 只许读改外部文件的禁令理由；docx/pptx 转 PDF/PNG 只有 Office COM 一条路
metadata:
  type: project
---

**环境事实（2026-08-24 实测复核，推翻 0818「没装 node」的记载）**：本机有 node v22.14.0 / npm 10.9.2（另有 Vercel CLI，批改工具部署用）、openpyxl 3.1.5、pandas 2.2.3、python-docx 0.8.11、python-pptx 1.0.2、pypdf 6.7.1、defusedxml 0.7.1、**pywin32 与 Microsoft Office 本体（Word/PowerPoint/Excel）**。仍没有的只剩 LibreOffice、pandoc、markitdown。故官方 skill（user 级 `anthropic-agent-skills` 市场，0818 装）的「新建」路径（docx-js／pptxgenjs）跑得通，xlsx 整体可用，pdf 各项可用，`scripts/office/validate.py` 可用；只有「读取」路径（pandoc／markitdown）跑不通。

**官方 skill 作用域＝只读改外部文件**（体检外部平台 pptx、拆第三方 docx、合并 pdf）。本仓一切交付产物一律走 laojohn-* 流水线。**禁令理由与环境无关**：官方件产出不带品牌版式、绕过 `--header-left/--header-right` 页眉参数与 `plan_link.py` 闸门。0818 时环境天然挡着「想违反也违反不了」，0824 起挡住它的只剩纪律，禁令一个字不松。别为跑通 pandoc／markitdown 去装 LibreOffice／pandoc——与本仓已成熟产出链重复造轮子。

**docx/pptx → PDF/PNG 只有 Office COM 一条路**（没有 LibreOffice）：Word `win32com.client.Dispatch("Word.Application")` → `ExportAsFixedFormat`；PowerPoint `Slides(i).Export(png, "PNG", w, h)`。已在 `laojohn-ppt\tools\shot_assets.py` 跑通并封装，取图直接用它。三个坑（脚本头注释也写了）：① 目标文件被 Word/WPS 打开会拿只读句柄或卡住；② `Quit()` 必须放 finally，否则留后台进程；③ **同一份文件要导多页必须一次会话导完**——`Quit()` 后 PowerPoint 要几秒才真退出，期间再 Dispatch 会让下一次 `Presentations.Open` 失败，报错却写成「发生意外」，指向完全错的方向（实测踩过）。

相关：[[writing-correction-tool-vercel-deploy-0824]]、[[ppt-delivery-boundary-0902]]。
