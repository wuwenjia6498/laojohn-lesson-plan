---
name: repo-slimming-plan-0920
description: 仓库瘦身已执行完毕（0920）：filter-repo blob-id 模式剥 583 个死二进制，759.67→303.40 MiB，内容零变化已证；含五条可复用的踩坑
metadata:
  type: project
---

2026-09-20 体检、演练、**当日执行完毕**。方案全文在**仓外**：`C:\Users\69491\.claude\plans\git-1-gb-breezy-lamport.md`（含全部可复制命令、双机时序、回滚卡片）。本条只留跨会话不可推断的结论。

## 体检结论：病灶是死历史，不是活文件

- 真实 `size-pack` **758.78 MiB**，远端 636MB。⚠ **`du` 显示 1009MB 是 exFAT 簇放大**（1MB 簇 × 204 个松散对象），**看体积一律用 `git count-objects -vH`，别看 `du`**。
- 全历史 blob 774.4MB 中 **364.5MB（47%）已不在 HEAD**，全是本该按 §8 挡住的渲染产物（`看图写话输出/`、`课程打包输出/*.zip`、`阅读单输出/` 等已改名或已删目录）。
- 另有 **93MB 躺在 HEAD 上、文件名自称作废**：`看图写话详案输出/_已失效-0728排期改版/` 14 个 48.38MB（**至今无任何 ignore 规则覆盖**）+ 各处 `图位/_历史/` 13 个 50.98MB。后者的根因是**gitignore 对已跟踪文件不生效**——规则 0728 才补，文件早已入库。**这是以后加任何 ignore 规则都要配 `git rm --cached` 的判据。**
- 月增量（未压缩）：6月 103.6 / 7月 350.6 / 8月 202.0 / 9月(至20日) 117.6 MB。

## GitHub 的真实上限

**仓库体积无硬上限**，只有推荐值，且官方两页口径不一（「理想<1GB、强烈建议<5GB」 vs 「on-disk 推荐 10GB」）。**硬限只有两条：单文件 100 MiB、单次 push 2 GB。**

⚠ **force push 要传全仓约 303 MiB**（0920 演练实测：建 bare 仓装旧历史当假远端，force push 新历史，`Total 7171 (delta 4214)`，303.15 MiB）。**2GB 上限无虞，但吞吐是真瓶颈。**

⚠⚠ **「只传 commit+tree 约 3.6MB」这个推算当天先立后废，是错的，别再用**。幸存 blob 的 SHA 确实一字不变（验过 pptx/jpg/md 三样），**但没用**——历史重写后两段历史**没有共同提交**，git 靠提交图遍历把「远端已有」标记为 uninteresting，没有共同祖先这条路就断了，全部对象重新上传；`backup/` 分支也救不了（实验里假远端同时挂 main 与 backup 两条旧分支，照样传满）。**得出 3.6MB 的那条命令 `git rev-list --objects HEAD --not <旧ref>` 在历史不相交时给不出真实推送量——别再拿它估推送**。
**上传速率 0920 已实测**（建一次性私有仓推两批 50MB）：**2.80 MiB/s** 与 **1.73 MiB/s**（后者 168 个小文件、每对象开销更高，更贴近真实推送的对象构成）。→ **303 MiB 约 2–3 分钟，留余量按 5 分钟算**。
⚠ **[[two-person-sync-0820]] 记的「73MB 推 10 分钟没完」（0.12 MB/s）已不复现，快了 15 倍**——那是一次性网络异常或早期状况，**别再拿它当规划依据**；但也别反过来当保证，执行前照样盯 `--progress`。

## 方案要点（三条不可推断的选型）

1. **用 `--strip-blobs-with-ids` 而非 `--path`**。按目录删会连 52.9MB 的 md/json 改稿历史一起毁（`课案输出/`→`读书会详案输出/` 这类改名目录里全是详案 md 的前世）；且 `角色册/妆-0N_*.png`、`写作课件PPT输出/` 属**路径活、版本死**，`--path` 根本删不掉。blob-id 名单＝全历史−HEAD，**数学上保证 HEAD 一字节不变**，且中文/空格路径的编码问题整条消失。
2. **B 机用 `fetch + reset --hard + gc`，不重新 clone**。重新 clone 要先删工作目录，而那正是 `.claude\memory` 那条 `mklink /J` 的目标路径——**断了不报错**。⚠ **这与 CLAUDE.md §8「两台机器重新 clone」冲突，执行后须同步改掉那句话。**
3. **Git LFS 已明确否决**：照样要重写历史（成本一样收益更少）；带宽额度 1GB/月按下载量计；filter 没装时文件变成指针文本、**打不开而不报错**。推翻条件＝HEAD 活二进制破 1GB 或单文件逼近 100 MiB。

## 已执行的两步（0920）

- **`git gc --no-prune`**：松散对象 204→0，`du` 1009MB→802MB。真实体积没变（那得靠重写）。
- **打了救生 tag `salvage/0805-honbei-dropped`**（指向 `b0ce4d57`，2026-08-05 honbei-dev 被丢弃的分支尖端，`docs/handoff/` 两份 0729 交接件与 `tests/README.md` 改动均未进主线）。⚠ **本地已打、尚未推远端。**

## ⚠ 两条最容易踩的

- **手工 gc 一律 `--no-prune`，禁 `--prune=now`**。实测 A 机当时有 10 个不可达提交，其中一个含未进主线的工作，`--prune=now` 会无声销毁它。
- **`clone --mirror`、`bundle --all`、`filter-repo` 三者都只处理可达对象**——不可达提交它们一个都救不了，而 filter-repo 会自动 `reflog expire + gc --prune=now` 全部销毁。**动手前必须先 `git fsck --unreachable` 查一遍，有价值的先打 tag 变成可达。**

## PNG 压缩：实测否掉了 PIL 路线

`optimize=True` 在这批图上**净变大 5%**（`备-03.png` 2.92MB→6.24MB）——原编码器已做过逐行 filter 择优，PIL 只试固定策略反而更差。本机 oxipng/zopflipng/optipng/pngcrush/ImageMagick **一个都没装**。WebP 无损实测省 27%（64MB）但要改扩展名与取图链路，已否。→ 方案里改成条件项：先 `pip install pyoxipng` 干跑，**省不到 15MB 就跳过**。

## 0920 演练已完成（零冻结 · 临时克隆 · 全部通过）

在 `C:\Users\69491\git-backup\dryrun` 上完整跑通 ⓪.3→③ 全流程，**四条验证全过**：
- **size-pack 759.67 MiB → 303.34 MiB**（比方案预估的 390MB 更好），packs 2→1
- 与源仓库 diff **只有阶段①那 21 个文件**，别无他物；**HEAD 树指纹重写前后完全一致**（内容零变化的最强证据）
- 三个受保护目录 **315 个文件 SHA+大小全部一致**；救生 tag 存活；358 个提交一个没少（预期的「空提交被剪」没有发生）
- 耗时：克隆 800MB **8.3 s**、名单推导 0.5 s、阶段① 0.9 s、**filter-repo 仅 4.4 s**——A 侧本地环节合计不到 1 分钟

⚠ **演练照出一条方案会卡死的前置**：**exFAT 卷不记录属主，git 拒绝从项目路径克隆**（阶段⓪ 的 `clone --mirror` 第一步就会失败）。已修：`git config --global --add safe.directory 'E:/laojohn-lesson-plan'` 与 `.../.git` 两条，本机已加。

## 冻结时段怎么定

**唯一的大变量是到 GitHub 的上传速率**（要传 303 MiB），其余全部实测完毕。**先建一次性私有仓推 50MB 计时再删**（做法在方案 ④.0），拿到速率再跟对方约——0.12 MB/s 要 42 分钟，5 MB/s 只要 1 分钟，差 40 倍。

**冻结期的唯一禁令是「不提交、不推送」——文件照常编辑、docx 照常渲**；B 只需在两个时点各到场约 10 分钟（T0 确认干净、T6 重新落地，后者要下载 303 MiB）。
→ 推荐约法＝**一个晚上**（对方下班前回 T0 三连，A 当晚跑完，次日上班前对方跑 T6），谁都不用等谁。通知对方的原话模板在方案文件 ④.0。

## 执行结果（2026-09-20 当日完成）

| | 前 | 后 |
|---|---|---|
| size-pack | 759.67 MiB | **303.40 MiB** |
| packs / 对象 | 2 / 8033 | 1 / 7207 |
| 跟踪文件 | 1413 | 1393 |

- **阶段①**（`b620604`）：摘除 25 个自证作废件 93.0MB，补泛化 ignore 规则；保留 `_已失效` 下 5 个 md。
- **阶段② PNG 重压：跳过**。oxipng 实测只省 15.7MB（占 303MB 的 5.2%），而做它就必须让 B 机改回 `reset --hard`、冻结期改动全部手工拷进拷出——不值。
- **阶段③**：filter-repo 剥 583 blob / 380.4MB，**5.5 秒**；force push 303 MiB **1 分 12 秒**（实际约 4.2 MiB/s）。
- **验证全过**：与备份镜像 diff 只有阶段①那 21 个文件；**HEAD 树指纹重写前后完全一致**（`acd085ba…`）；受保护三目录 315 文件 SHA 全不变；362 提交一个没少；120 pptx / 329 图 / 192 docx 完整性零损坏。
- 远端留 `backup/pre-filter-20260920`（旧历史全量）与 `salvage/0805-honbei-dropped`。**观察期到 2026-10-04**，其间无异常即可删 backup 分支（删之前 GitHub 网页显示的仓库体积不会降，属正常）；salvage tag 确认无用后再删。

## ★ 核心通则：GC 根必须先摘干净（0920 由 B 机同事归纳 · 本次发作四回）

**`gc --prune=now` 只对「没有任何 GC 根指着」的对象生效。动手前必须把这六类根逐个摘干净，否则瘦身完全空转：**

| GC 根 | 本次怎么发作的 |
|---|---|
| **stash** | 她有 2 条旧 stash，以旧 main 为父，整段旧历史因此可达。**本条是她发现的，我的方案原本完全没提** |
| **索引（index）** | 我让她用 `reset --soft`，索引停留在旧 HEAD、仍引用被删的 93MB blob；索引是 GC 根，于是第 4 步一个对象都清不掉。**她改用 `--hard` 才对** |
| **远程跟踪 ref** | 我给的 `git fetch origin --prune --force` 会把 `backup/pre-filter-20260920` **整支旧历史拉到本地**——命令清单自己抵消了瘦身效果 |
| **本地分支** | 她那边有 `backup-0820-before-rebase`（独有对象 470.7MB）与 `worktree-wl-5a-unit4`（540.1MB）；**我的清单完全没提到**。我这边则是 filter-repo 把 `refs/remotes/origin/backup/*` 迁成了本地分支 |
| **worktree** | 上面那条还挂着注册 worktree，得先 `git worktree remove` |
| **tag** | 本次无碍（救生 tag 是有意保留的） |

**动手前的自查一条龙**：
```bash
git stash list
git diff --cached --numstat | wc -l          # 索引与 HEAD 的差异，须 0
git for-each-ref                             # 看全部 ref，含本地分支/远程跟踪/tag
git worktree list
```

⚠ **我自己也栽在同一条上**：验证时跑 `git fetch backup <镜像>` 把整段旧历史拉回本地，仓库一度涨到 **938.17 MiB（比重写前还大）**。清法＝删掉多余本地分支 + `reflog expire --expire=now --all && gc --prune=now`，回到 303.41 MiB。
**已装长效防线**：`git config --local --add remote.origin.fetch '^refs/heads/backup/*'`（负向 refspec，git ≥2.29），否则日后任何一次 `git fetch` 都会把保命分支的旧历史重新拉回来。**两台机器都要装。**

⚠ **`git cherry` 在历史重写后不可信**：重写改了 patch-id，会把早已在 main 里的提交报成「无等价」（她实测 36/33 条全是假阴性）。判断分支上的工作是否已进主线，要**逐路径核内容**，不能看 `git cherry`。

⚠ **`reset --hard` 不会删「已被新 gitignore 忽略」的文件**：那 93MB 作废图仍在两台机器的硬盘上（已脱离 git 跟踪）。要腾本地空间只能手动删；**别用 `git clean -Xfd`**，它会连 docx/pdf/pptx 渲染产物一起删。

## ⚠ 五条踩坑（下次碰 git 批量操作直接用）

1. **exFAT 卷不记录属主，git 拒绝从项目路径 clone**——`clone --mirror` 第一步就会失败。已永久修：`git config --global --add safe.directory 'E:/laojohn-lesson-plan'` 与 `.../.git`。
2. **`git ls-files` 默认把中文转义成八进制**，`grep '中文'` 必然零命中——**会造出「校验通过」的假象**。凡对中文路径做 grep 校验，一律加 `-c core.quotepath=false`。本次因此误判过一次。
3. **`git cat-file --batch-check` 的格式串必须带 `%(rest)`**，否则 `rev-list --objects` 的「SHA 路径」两段会被当成一个对象名，全部报 missing。
4. **`git rm --cached` 批量传路径时，一条不存在就整批中止**——目录级删除会先带走子目录里的文件，后续按文件名再删就撞空。用 `--ignore-unmatch` + 去重后的 `--pathspec-from-file=- --pathspec-file-nul`。
5. **robocopy 搬不动含 `·`／全角括号的中文路径**，静默失败；改用 Python `shutil.copy2` 逐个拷。

## 四个拍板点（0920 均已采纳并执行）

A 那 93MB 作废件只留本地？ · B 角色册 26.6MB 旧母版一并剥离并改 `.gitignore` 注释？ · C 改名前目录的历史 pdf/png/docx 全剥（**md 文字历史全保留**）？ · D 用 `fetch+reset+gc` 并改 CLAUDE.md §8？——四条均建议采纳。四条全部采纳并已执行。冻结时段：当日午后，B 机同事按 T0 三条自检达标后进入冻结。
