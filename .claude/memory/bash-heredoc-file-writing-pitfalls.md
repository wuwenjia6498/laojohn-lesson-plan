---
name: bash-heredoc-file-writing-pitfalls
description: 用 Bash heredoc 写代码文件的三个坑：超长会被静默截断、源码里的反斜杠会被吞掉一层（单→折行、双→折成单）、替换失败后重跑前必须先查半成品残留
metadata:
  node_type: memory
  type: feedback
---

本机用 `cat > f <<'EOF'` 写 .py/.js/.css 等代码文件时踩到的三件，都不是语言问题、是工具层：

1. **超长 heredoc 会被截断**，报 `unexpected EOF while looking for matching '`，且行号指向不存在的位置。实测约 150 行以上就不稳，90 行左右安全。**解法：分块 `>>` 追加，每块写完立刻语法检查**（`python -c "ast.parse(...)"` / `node --check`），出错也好定位。

2. **源码里的反斜杠会被吞掉一层**，两种形态，第二种更隐蔽。① 写 JS 的 `split(/\n+/)` 这类正则时，落盘变成正则中间断行、语法直接坏。② **双反斜杠折成单反斜杠**（2026-08-27 又踩两次）：python 替换脚本里写 `"\\n"`（本意是落盘一个字面 `\n`）实际落盘成**真换行**，`print("` 当场断行报「unterminated string literal」；写 `"\\25BE"`（本意是 CSS 转义 ▾）落盘成 `"\25BE"`，python 当八进制读成控制字符 0x15，浏览器把它连同后面的 `BE` 一起画成「□BE」。**凡 CSS 转义／正则／字符串转义带反斜杠的一律中招。****解法：反斜杠一律用 `chr(92)` 拼、换行用 `chr(10)` 拼**（源码里一个字面反斜杠都别留，内容里要出现反斜杠就先写占位符再 `.replace`）；**能用真实字符就别用转义**——CSS 的 `content` 直接写 `"▾"`，文件是 UTF-8，没有任何问题。

3. **替换脚本 assert 失败后，重跑前必须先查半成品**。我遇到过 `assert old in s` 莫名失败（同一字符串肉眼可见就在文件里），改用按行号切片替换后成功——但此时上一次的失败其实**已经部分写入**，于是同一个函数被插了两份；再写删除脚本又因为两份位置重叠、把两份一起删光。**解法：每次替换前先 `grep -c` 数一遍目标出现几次**，别默认失败＝没写。

**Why:** 这三件都**不会报错到点子上**——截断报的是引号不匹配、转义折行报的是正则语法、重复插入报的是「标识符已声明」。照报错去查会一路查错方向。

**How to apply:** 写代码文件默认分块（≤90 行）+ 每块即时语法检查；含反斜杠的内容用 `chr(92)` 拼；任何「明明在文件里却匹配不上」的替换，先数出现次数再动手。同族的写文件工具坑见 [[write-tool-normalizes-curly-quotes]]（Write 吞弯引号）与 [[fix-quotes-breaks-code-blocks]]（fix_quotes 毁代码块）。

---

**追加两件（2026-08-21，改 skill 规则文件时踩到）：**

4. **定界符漏了引号 → shell 把内容里的反引号当命令替换执行。** 写 `<<PYEOF`（不带引号）而非 `<<'PYEOF'` 时，正文里所有 `` `unit-texts.md` `` 之类会被 shell 执行成命令，报一串 `command not found`，**然后替换成空字符串写进文件**——脚本本身照常打印 `[OK] 替换 1 处`，**看起来完全成功**，实际写进去的是 `唯一事实源＝,**禁止…`（路径整个没了）。反引号在 md 里到处都是（路径、文件名、字段名），所以这个坑在本仓必然复发。**解法：heredoc 定界符一律加引号；写完 `grep -o '`xxx.md`'` 数一遍反引号内容还在不在。**

5. **手写 unicode 转义会打错字，且错得很隐蔽。** 为绕开「弯引号被打直」而改用 `\uXXXX` 拼中文，两次打错——「抛」写成「招」（U+629B→U+62DB，导致 anchor 找不到）、「摊开」写成「摧开」（已写进文件才发现）。**中文不该手写转义。解法：正文中文直接写（`<<'EOF'` 不会动它），只有弯引号用常量拼**——scratchpad 里的 `patch.py` 就是为此而写：`CQ/CQR/SQ/SQR` 四个常量 + 读写都带 `newline=''` 保 CRLF + 替换前断言命中数。改本仓 md 规则文件直接复用它。

6. **读写文件不带 `newline=''` 会把工作区 CRLF 整体换成 LF**，`diff` 立刻炸成全文（实测 417 行），而 `git diff --numstat` 只显示真实的 9/2——**因为仓库存的是 LF、autocrlf 在起作用**。别被 `diff` 吓到去回滚，以 git 的统计为准；但工作区仍应转回 CRLF 保持一致。 **⚠ 但「以 git 统计为准」只在仓库存 LF 时成立**（2026-08-25 订正）：本仓 `MEMORY.md` 在仓库里存的是 **CRLF**（实测 159 CRLF + 3 裸 LF 的混合），而 `core.autocrlf=true` 会把工作区 CRLF clean 成 LF 再入库——于是 `git diff --cached` 同样炸成全文（163/160），**放行就是真把全文改写提交进去**，双人协作时对方合并会爆炸。故动手前先查一句仓库里存的是什么：`git show HEAD:<file>` 数 CRLF。仓库存 LF → 照旧以 git 统计为准；**仓库存 CRLF → 必须按 HEAD 字节重建**：取 HEAD 原始字节，用 `difflib.SequenceMatcher` 比对「去掉行尾后」的两组行，`equal` 段保留 HEAD 原行尾、改动段才用新内容，写回后以 `git -c core.autocrlf=false add` 暂存。实测把 323 行噪声压回真实的 7 行。

7. **`open(f, 'wb')` 先截断文件，异常发生在 write 的参数里就会把文件清成 0 字节。**2026-08-25 实测：`open(f,'wb').write(d.replace(old, old + ' ' + new))` 因 bytes 拼 str 抛 `TypeError`，但截断已经发生——一条 TypeError 清空了一份记忆文件，且报错信息完全指向类型问题、不会提示文件已毁。**解法：把内容全部算完并断言通过，最后一步才 `open(...,'wb')`**；二进制改写时 old/new 两侧都要 `.encode()`，别只 encode 一半。真清空了也别慌：已提交过的文件 `git checkout HEAD -- <file>` 即可完整恢复。

**补（2026-08-27 实测）**：这条坑在 python 侧的等价形态是 **`pathlib.read_text()` + `write_text(..., newline='')`**——read 把 CRLF 读成 LF、write 原样写出，**一次调用就把整份文件行尾改掉，全程零提示**。本次一口气改掉了详案与两个 references 文件，直到「后一次替换 0 命中」才暴露。**改本仓 md（全部 CRLF）一律 `write_bytes` 显式重建 `
`，改完 `file <路径>` 复核一次行尾。**
