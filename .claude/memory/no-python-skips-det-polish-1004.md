---
name: no-python-skips-det-polish-1004
description: 有一台机器没有 Python 时，写作课 5.0 确定性润色会静默缺席，成稿口语残留多；须人工按 prose-exemplars 补一遍
metadata:
  type: project
---

2026-10-04 生成四上六《中国的世界文化遗产》详案时，当时这台机器上 `python` 只有 Microsoft Store 占位别名（exit 49），系统里找不到真正的解释器。因此 avoid_card、polish_writing（5.0）、tone_gate、essay_audit、docx 引擎全部没跑。

后果：生成时虽然读过 `prose-exemplars.md`，成稿仍残留大量措辞层问题（念、哪儿、挑、跟、要紧、宣告式「这次讲评看两样：」、省主语短句）。冷审 detail-review 按规定也不手工做成批替换。用户事后要求「按 prose-exemplars 优化」，才人工补了一遍。

**Why:** 本线设计就是把措辞层从生成侧后移（见 generation-brief §二）：生成时只一次性定调、不逐句核对，机械替换交给 5.0 脚本，行文细修交给冷审 Pass B。脚本跑不了，这一层就整个缺席，而且不报错。

**已补装（2026-10-04 同日）**：经 winget 装了 Python 3.13.15，按用户级安装，路径是 `%LOCALAPPDATA%\Programs\Python\Python313`，在用户 PATH 里排在 WindowsApps 占位别名之前。依赖照 `_交接/交接说明.md` 第三节装齐，另加 numpy、opencv-python、fonttools、pymupdf、pywin32、requests、httpx、openai、google-genai、fastapi、uvicorn、python-multipart，以及 playwright chromium。四上六这份详案的 tone_gate、essay_audit、5.0 dry-run、docx 导出都已跑通。⚠ 装之前就开着的终端或会话，PATH 是旧的，`python` 仍会指向占位别名，要重开，或改用全路径。

**How to apply:** 遇到机器没有 Python 时，在派冷审之前，先人工对照 `polish_rules.py` 的规则表和 `prose-exemplars.md` 过一遍师话层，并主动告诉用户 5.0 没跑。装上 Python 后补跑 `--stage det` 与 tone_gate。相关：[[writing-correction-tool-0818]]。
