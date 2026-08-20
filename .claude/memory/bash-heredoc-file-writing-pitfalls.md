---
name: bash-heredoc-file-writing-pitfalls
description: 用 Bash heredoc 写代码文件的三个坑：超长会被静默截断、源码里的反斜杠转义会被折成真换行、替换失败后重跑前必须先查半成品残留
metadata:
  node_type: memory
  type: feedback
---

本机用 `cat > f <<'EOF'` 写 .py/.js/.css 等代码文件时踩到的三件，都不是语言问题、是工具层：

1. **超长 heredoc 会被截断**，报 `unexpected EOF while looking for matching '`，且行号指向不存在的位置。实测约 150 行以上就不稳，90 行左右安全。**解法：分块 `>>` 追加，每块写完立刻语法检查**（`python -c "ast.parse(...)"` / `node --check`），出错也好定位。

2. **源码里的 `\n` 会被折成真换行**。写 JS 的 `split(/\n+/)` 这类正则时，落盘变成正则中间断行、语法直接坏。**解法：反斜杠一律用 `chr(92)` 拼**（`"@NL@".replace("@NL@", chr(92)+"n")`），或先写占位符再替换。

3. **替换脚本 assert 失败后，重跑前必须先查半成品**。我遇到过 `assert old in s` 莫名失败（同一字符串肉眼可见就在文件里），改用按行号切片替换后成功——但此时上一次的失败其实**已经部分写入**，于是同一个函数被插了两份；再写删除脚本又因为两份位置重叠、把两份一起删光。**解法：每次替换前先 `grep -c` 数一遍目标出现几次**，别默认失败＝没写。

**Why:** 这三件都**不会报错到点子上**——截断报的是引号不匹配、转义折行报的是正则语法、重复插入报的是「标识符已声明」。照报错去查会一路查错方向。

**How to apply:** 写代码文件默认分块（≤90 行）+ 每块即时语法检查；含反斜杠的内容用 `chr(92)` 拼；任何「明明在文件里却匹配不上」的替换，先数出现次数再动手。同族的写文件工具坑见 [[write-tool-normalizes-curly-quotes]]（Write 吞弯引号）与 [[fix-quotes-breaks-code-blocks]]（fix_quotes 毁代码块）。
