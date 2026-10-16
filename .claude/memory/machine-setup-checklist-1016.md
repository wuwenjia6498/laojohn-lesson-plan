---
name: machine-setup-checklist-1016
description: 换机/重装后照 docs\换机装机清单.md 做、跑 setup_check.py 自检；1016 重装 Claude Code 实测缺的东西与三个坑
metadata:
  type: project
---

2026-10-16 本机重装 Claude Code（新装 Python 3.15）后补装，整理成三件套：`docs\换机装机清单.md`（步骤）＋根 `requirements.txt`（全仓依赖）＋根 `setup_check.py`（只读自检，[缺] 即退出码 1）。三处要一起改。

**Why:** 重装后 python-pptx/Pillow/pypdf 等缺一半、ffmpeg 没有、海报毛笔字解码包缺——都是跑到一半才炸或静默退化（毛笔字静默退回楷体）。

**How to apply:** 用户说换电脑/重装/「缺东西」时，先跑 `PYTHONUTF8=1 python setup_check.py`，按 [缺] 补；新增任何第三方 import 或外部程序，同步进 requirements.txt 与 setup_check.py。

三个坑：
- Python 3.15 下 brotli、pyyaml 无现成 wheel，整批 pip install 会全失败——brotli 用 brotlicffi 替代（fontTools 认），pyyaml 只 skill-creator 用、加了版本标记跳过。
- 新版 winget 装 Gyan.FFmpeg 不放 WinGet\Links 别名、改写用户 PATH，当前会话找不到；`ffmpeg_path.py` 已补 WinGet\Packages 回退。
- 本机 `课件配图工具\课件产出\` 无 AI 图（不入库），用户定不重新生成：**别在本机重烘 v9 读书会 PPT 正式件**，会出没图的件。

自检话术已换成只在记忆里的问题，见 [[two-person-sync-0820]]；相关 [[editor-unsaved-edits-lost-1015]]。
