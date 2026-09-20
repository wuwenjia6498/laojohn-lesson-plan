# 手绘风格库 · 本仓副本（只放用到的部分）

来源：用户级 skill `handdraw-style-prompter`（GitHub `yang0/handraw-style`，MIT 许可，见同目录 LICENSE 文件），
装在 `%USERPROFILE%\.claude\skills\handdraw-style-prompter\`，**不在本仓**。同事机器不一定装了它，所以：

- `styles.json`：274 条风格索引整份拷贝（约 100 KB），`gen_illustration.py` 解析编号时优先读这里。
- `refs\<编号>.webp`：**只放用过的编号**的参考图。首次用某编号时脚本自动从用户级包拷一份进来并入库，
  之后同事机器不装风格库也能重生同一风格。整包 25 MB 不拷。
- 编号怎么选：打开用户级包里的 `skills\handdraw-style-prompter\gallery\index.html` 浏览；静物友好的候选见 `../../references/illustration-prompt.md`。

风格库更新后想同步索引：把上面路径的 `references/styles.json` 重新拷过来即可（编号语义不变）。
