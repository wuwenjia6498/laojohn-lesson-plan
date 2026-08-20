---
name: fix-quotes-breaks-code-blocks
description: "fix_quotes_md.py 会把 ``` 代码块里的引号也转成弯引号，粘出去的命令直接跑不了；跑完须回扫代码块"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ff546aad-e88b-4dc8-b110-f1b025541362
  modified: 2026-08-07T04:36:12.114Z
---

`fix_quotes_md.py` 做的是**全文件无差别替换**，不认 Markdown 代码块。2026-08-07 给《大头儿子和小头爸爸》图单跑完后，末尾那段 bash 示例里的 `--md "路径.md"` 被转成了 `--md "路径.md"`（弯引号），**用户复制粘贴会直接报错**。

**Why**：CLAUDE.md 的弯引号铁律本来就把「Markdown 语法/代码/英文路径」列为例外，但脚本实现不到这一层。检查工具 `check_quotes.py` 只统计字符数、同样不区分代码块，所以**这个破坏两道关都不报**——只有真去粘那条命令才会发现。图单、SKILL.md、README 这类**正文要守弯引号、又带命令示例**的文件是重灾区；纯详案没有代码块，所以以前没撞上。

**How to apply**：对含 ``` 代码块的 md 跑完 `fix_quotes_md.py` 后，**回扫一遍代码块把引号还原成半角**（按 ``` 行切换 in/out 状态，只处理块内）。还原脚本留在会话 scratchpad，逻辑就十来行，重写比找旧文件快。

顺带两条：① 引号已被转弯之后再用 Edit 定位会很别扭，直接写 python 脚本按不含引号的锚点替换更稳（同 [[write-tool-normalizes-curly-quotes]]）；② 在 Bash 工具里写含中文弯引号的 python `-c` 单行会踩 shell 转义，改用 heredoc 或写临时 .py 文件。
