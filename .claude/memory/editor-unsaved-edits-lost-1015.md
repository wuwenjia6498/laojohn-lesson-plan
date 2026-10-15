---
name: editor-unsaved-edits-lost-1015
description: 用户在 Cursor 里手改 md 未保存，我的脚本读写磁盘把修改冲掉；已开 Cursor 自动保存，改用户正开着的文件前仍要提醒
metadata:
  node_type: memory
  type: feedback
  originSessionId: 256aeb95-8858-48df-bbaa-44b28dafc688
  modified: 2026-10-15T03:27:49.055Z
---

2026-10-15《孤独的小螃蟹》详案：用户在 Cursor 里手动删句、改稿但没保存，我用 python 脚本从磁盘读→写回改目录并提交，用户的修改全丢（磁盘与三次提交里都从没出现过那些修改）。我只能看到磁盘，看不到编辑器未保存的缓冲区。

**Why:** 用户的手改是接力生产的一部分，丢了等于白干，且事后无从恢复。

**How to apply:**
- 已在 `%APPDATA%\Cursor\User\settings.json` 开 `files.autoSave: afterDelay`（1 秒）。若发现该设置被关，先提醒用户。
- 用户刚在 IDE 打开/选中过某文件、又让我改它时，动手前一句话提醒「先保存编辑器里的修改」；改完后 git diff 看一眼有无用户手改混入，并在汇报里点出。
- docx 被 WPS 锁＝用户可能在 docx 里改稿：重渲前先比对 docx 正文与 md，有差异停下问，不直接覆盖。同族：[[external-docx-backfill-0902]]
