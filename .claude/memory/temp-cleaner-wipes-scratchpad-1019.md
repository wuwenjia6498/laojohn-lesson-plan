---
name: temp-cleaner-wipes-scratchpad-1019
description: 本机360「清理Pro」常驻服务定时删%TEMP%下未占用的旧文件（含scratchpad），删文件留目录；跨小时要复用的脚本/备份放持久目录
metadata:
  type: feedback
---

本机装有 360「清理Pro」（服务 `SysCleanProService`，`%APPDATA%\SysCleanPro\`，自动启动）。它会定时扫整个 `%TEMP%`，把**没被占用、超过约 1–2 小时**的文件删掉，目录留着（表现为 scratchpad 只剩子目录和 `__pycache__`）。2026-10-19 排查时核实：`%TEMP%` 里超过 2 小时的文件剩 36 个，全部都是被其他程序锁住的；会话记录里也没有任何删除 scratchpad 的命令。

**Why:** 10/18–10/19 阅读单批修、姆咪核查两次长会话里，脚本和备份被清掉，只能重写；之前误以为是 Claude Code 自己清理。

**How to apply:**
- scratchpad 只放一次性中间件。跨小时还要用的脚本、备份、改原件前的快照，一律放持久目录（如 `%LOCALAPPDATA%\<任务名>\`，参考 [[worksheet-blank-box-fix-1019]] 的 `laojohn-wsfix`）。
- scratchpad 文件不见了，先想到是这个清理服务，不要当成自己误删去排查命令。
- 用户若已在清理Pro里关掉自动清理、加了白名单或卸载了它，以实际情况为准（放一个测试文件，隔 3 小时再看还在不在）。
