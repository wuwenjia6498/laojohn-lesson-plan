# 手绘风格库 · 本仓副本（只放用到的部分）

来源：用户级 skill `handdraw-style-prompter`（GitHub `yang0/handraw-style`，MIT 许可，见同目录 LICENSE 文件），
装在 `%USERPROFILE%\.claude\skills\handdraw-style-prompter\`，**不在本仓**（私有仓库与装法见 `docs\协作同步说明.md` 五点五节）。
同事机器不一定装了它，所以：

- `styles.json`：274 条风格索引整份拷贝（约 100 KB），解析编号时优先读这里。
- `style_tags.json`：274 条按用途标签（媒介／年龄感／题材／基调／色彩／人物造型＋「写作课招生」推荐／慎用／不推荐档与理由），封闭词表，2026-09-24 看参考图逐条打的。挑海报编号先看「写作课招生」，给读书会的书配图按书的气质组合筛（词表与用法见用户级包 `SKILL.md`「按用途挑风格」）。
- `refs\<编号>.webp`：**只放用过的编号**的参考图。首次用某编号时脚本自动从用户级包拷一份进来——
  **请随项目 json／海报 json 一并提交**，之后同事机器不装风格库也能重生同一风格。整包 25 MB 不拷。

**谁在用（2026-09-24 起两家共用这一份，原在 `laojohn-writing-poster/assets/handdraw/`）**：

| 用处 | 怎么给编号 | 解析入口 |
|---|---|---|
| 课件配图工具 | 风格卡字段 `手绘编号`（网页新建项目表单 / 风格卡里填；命令行 `build_specs.py --handdraw`） | `scripts/run_lesson.py` 的 `compose()` |
| 写作课单元海报 | `illustration.style` 或 `--style` | `laojohn-writing-poster/scripts/gen_illustration.py` |

两家都经 `scripts/handdraw_style.py`（单一源，禁复制）取特征、上色句与参考图说明；改它两家都要回归。

编号怎么选：打开用户级包里的 `skills\handdraw-style-prompter\gallery\index.html` 浏览；静物友好的候选与已验证编号见
`.claude/skills/laojohn-writing-poster/references/illustration-prompt.md`。274 条特征 2026-09-24 已全部改成可见特征分项写法（19 条 0923 手调、其余看图起草）；用户级包里的画廊卡片显示标签，可按标签搜索。

风格库更新后想同步：把用户级包里 `skills/handdraw-style-prompter/references/` 下的 `styles.json` 与 `style_tags.json` 一起拷过来（编号语义不变）。
