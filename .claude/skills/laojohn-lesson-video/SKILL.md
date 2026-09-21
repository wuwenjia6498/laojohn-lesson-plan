---
name: laojohn-lesson-video
description: 把一份「老约翰」同步习作写作课详案 + 该课次的 PPT + 教师用配套，自动做成 15–25 分钟的「备课视频」——画面是老师手里那份 PPT 逐页推进，旁白讲「这一页你要讲什么／为什么这么设计／学生容易卡在哪」，带硬字幕，给加盟商老师上课前自学用。当用户提到备课视频/讲解视频/师训视频/把课案做成视频/给加盟商出个视频，或写作课 PPT 链跑完后说「出个视频」时使用。注意：旁白是备课解说不是示范课录音；读书会线暂不适用。
---

# 备课视频生产链

## 这支片子是什么

加盟商老师手里已经有详案、PPT、教师速览三份纸，缺的是**有人带他走一遍**。
本链把「教师用配套里的三色旁注（必守／可放开／为什么）+ 易错点」这层
**此前只印在一张 A4 上、从没人展开讲过**的内容，变成逐页讲解。

> **旁白不是念给学生听的课，是讲给老师听的备课。**
> 判据：把画面遮住只听声音，应该像一位老教研在带新老师过教案，不像一节课的录音。

写法判据的唯一源是 `references/narration-style.md` —— 生成、机检、人工审稿三处共用它，
`write_narration.py` 直接读它的原文注入 prompt，不另存口径。

## 前置

该课次必须**已跑完 PPT 后处理链**（`laojohn-ppt` 四步，含第 4 步页标回注）——
详案里没有 `〖PPT 第N页 · 页型 · 眉标〗` 就没有分镜骨架，本链直接拒绝执行。
目前 17 个课次具备条件；六上五、五上五、四上五、三上五四篇新稿要先补 PPT 链。

一次性准备：
- **ffmpeg**：`winget install --id Gyan.FFmpeg -e`（`ffmpeg_path.py` 会自动找 WinGet\Links，
  不必重开 shell）。⚠ Playwright 自带的那个不能用，是 disable-everything 构建、出不了 mp4。
- **外部终稿 pptx**：拷进 `_备课视频工作区\<课次>\source.pptx`（整目录 gitignore）。
  没有就加 `--fallback-repo-pptx` 用仓内 anim 版——实测仓内版版面完整、有插图，
  只是媒体被 256 色量化过，画面可用。

## 八步

```
1  build_shotlist.py   详案+教师用json+anim.json → <课次>-分镜单.json      零模型
2  write_narration.py  分镜单 → <课次>-旁白稿.json (+--export-md)          调模型
3  audit_narration.py  机检九项 + **闸门 A**（--by <人> 记账放行）          机检+人工
4  shot_frames.py      pptx → frames\p##.png（1920x1080）                  COM
5  synth_voice.py      旁白稿 → audio\*.wav + _配音清单.json（逐句）        调 TTS
6  build_timeline.py   → _时间轴.json / sub.srt / _audio.txt / _frames.txt  纯推导
7  render_video.py     → <课次>-备课视频.mp4（先 --sample 出样片＝闸门 B）  ffmpeg
8  package_video.py    → _交付包\（mp4 + srt + 使用说明 + 版本注记）   只复制
```

⚠ **第 2 步的质量靠的不是 prompt 里多写几句话，是第 1 步逐页算好的东西**。
`write_narration.py` 向模型逐页点名三样：该写哪几块（`_required_blocks_note`）、
手里有几条素材、起手式用哪一种（`LOCATE_/DO_/RISK_OPENERS` 三池取模）。
**写成通则的约束模型会漏，逐页点名的才执行**——这条总规律与三次实测见
`references/narration-style.md` §三.4。

```powershell
$env:PYTHONUTF8='1'
$u = "三上-第一单元-猜猜他是谁"
python .claude\skills\laojohn-lesson-video\scripts\build_shotlist.py $u
python .claude\skills\laojohn-lesson-video\scripts\write_narration.py $u --export-md
#   ← 通读 <课次>-旁白稿.md，改 json，然后：
python .claude\skills\laojohn-lesson-video\scripts\audit_narration.py $u --by 吴文佳
python .claude\skills\laojohn-lesson-video\scripts\shot_frames.py $u --check
python .claude\skills\laojohn-lesson-video\scripts\synth_voice.py $u --speed 1.1
python .claude\skills\laojohn-lesson-video\scripts\build_timeline.py $u
python .claude\skills\laojohn-lesson-video\scripts\render_video.py $u --sample 6   # 样片
python .claude\skills\laojohn-lesson-video\scripts\render_video.py $u              # 全量
python .claude\skills\laojohn-lesson-video\scripts\package_video.py $u
```

⚠ **第 4 步必须在 PowerShell 里跑**，不能走 Bash 工具——PowerPoint COM 要启动进程，
Bash 的沙箱会挡住，报的却是 `Presentations.Open : Failed`（像"文件被占用"，查错方向全偏）。

## 两道闸门

**闸门 A（旁白稿定稿）· 必设。** `audit_narration.py --by <人>` 把
`{plan_md5, shotlist_md5, narration_md5, by, at, issues}` 写进旁白稿 `meta.audit`；
`synth_voice.py` 启动校验三个 md5，对不上拒绝合成。逃生口只有 `--no-audit` 一个。

它拦的是两件实事：旁白是**对外件**，必须过人眼；**TTS 花钱**，改一个字就得重合成整页。

> **闸门守的是「审过」不是「全绿」**——issues 非空照样可以 `--by` 放行（同仓内既有口径）。
> 反过来**机检全过也不等于审完**：旁白讲得对不对、教学判断有没有说错，机器给不出。

**闸门 B（样片验收）。** 先 `render_video.py --sample 6` 出 5 分钟样片，人看过再全量渲。

## 四条硬口径

1. **页码权威源是详案内联页标，不是页标映射 json。**
   映射 json 在带跨页标记的课次会整体偏移——三上一实测它记 page 2–24，而详案是
   `2,…,18,19-20,21,…,25`、pptx 25 页，它把 `19-20` 记成一页、此后每页少 1。
   17 个课次里 9 个带跨页标记，且各课次行为不一致。映射只用来交叉校验、出偏移报告。

2. **`align_check` 对不上不许硬闯。** 它断言「详案覆盖页 + 封面 + 片尾 == pptx 页数」。
   用外部终稿时这道尤其关键：外部人工嵌图会加页/拆页，而失配的唯一表现是
   「旁白讲的和画面不是同一页」，不校验就只能靠看完 20 分钟片子才发现。
   对不上时人工确认后把确认人写进 `align_check.confirmed_by`。

3. **画面源取不到终稿就报错，不静默回退。** 静默回退会产出一批页码可能对不上的废片。

4. **逐句合成，不整页合成。** 字幕边界＝音频实测边界，零漂移，**不需要 TTS 返回
   字级时间戳**——选型时不必为这项能力付溢价。副作用还有两个好处：某句念错只重合成
   那一句；句间能插实体静音片段。

5. **「附：习作讲评」页不进片**。讲评环节只存在于详案，实际 PPT 里是删掉的；
   详案却给它留着页标，不丢就会拿它去配一页别的画面（三上一实测：配到了 THE END 页）。
   `drop_appendix()` 缺省丢掉，`--keep-appendix` 给真做了讲评页的课次留口。
   丢掉后腾出的那一页由 outro 认领，正好对上 THE END。

6. **字幕不叠在课件上**。输出 1920x1232：上方 1080 是课件画面（零遮挡），
   下方 152 是字幕带。课件底部常是本页的关键论点，叠字幕上去就盖住了。
   ⚠ **带高要按两行算**（`wrap()` 会折行，旁白均 28 字，两行是常态）：
   实际字号 = `FontSize/384*输出高`，要求 `MarginV_px + 两行高 ≤ BAR_H`。
   改 `BAR_H` 就必须重算 `SUB_SIZE`/`SUB_MARGIN`；水印 y 钉 `SLIDE_H`，不能用 `h`。

## 共享件（禁复制，改真源要回归）

| 用到的真源 | 谁的 | 本链怎么用 |
|---|---|---|
| `laojohn-ppt\tools\shot_assets.py` | ppt 线 | `shot_frames.py` importlib 薄壳调 `pptx_to_png_batch(src, jobs, size=)`。`size` 是本链新加的**可选**参数，默认 None 时宣讲件行为一字不变 |
| `课件配图工具\scripts\imgclient.py` | 配图工具 | `write_narration.py` 薄壳调 `make_client().chat()` |
| 根 `tone_gate.py` | 全仓 | **手动跑**，只看它的 INFO 层（起手式高密度、破折号计数、词频）。⚠ writing 档的 FAIL 层不适用于旁白稿视图 md（`**locate**：` 会被当成星号违规） |

薄壳按**相对路径**定位真源，改 skill 目录名或挪 scripts 会静默断链。

## TTS 通道

`TTS_PROVIDER` 一个环境变量切换，密钥三级回退（环境变量 → `scripts\.env` →
`tts.config.json`，后者 gitignore）。

| 通道 | 现状 |
|---|---|
| **`volc`（现行）** | 火山豆包语音合成模型2.0。**2026-09-21 已开通正式版**：APP ID 8950210010、后付费 0.0003 元/字、不限字数、并发 10、送 99 款音色。**音色＝渊博小叔 `zh_male_yuanboxiaoshu_uranus_bigtts`**（用户盲听四选一定下）。`cluster` 用 `volcano_tts`（大模型音色也是这个值）。**实测 5.29 字/秒，speed 用 1.0、不要加速** |
| `aihubmix` | OpenAI 兼容 `/v1/audio/speech`，复用现有 `AIHUBMIX_API_KEY`、零开通。⚠ 只有六个 OpenAI 英文音色，念中文是洋腔，实测只有 3.5 字/秒（要 `--speed 1.1` 硬加速听感发紧）——**只当应急备胎** |
| `minimax` | 纯 HTTP，接入最简单，未接 |

定音色的方法（已走过一遍）：拿**真旁白**（挑有必守、有卡点的重点页，不是漂亮句子）在几个候选音色各合一条，按三条判：**连听 20 分钟累不累、像不像老教研在说话（而不是播音或客服）、会不会抢走对内容的注意力**。
别凭官网 demo 选——demo 文本都是挑过的。99 款里先排掉角色扮演、视频配音、多情感那一大类。

**语速实测值写在 `_配音清单.json` 的 `rate_cps_measured`**，换通道后要拿它回写
分镜单的 `rate_cps` 再重算字数预算。

## 产物与入库

`写作课备课视频输出\<年级册>-第N单元-<题目>\`：

| 文件 | 入库？ | 为什么 |
|---|---|---|
| `<课次>-分镜单.json` | ✅ | 源。人工可改 env 对齐、kind、budget |
| `<课次>-旁白稿.json` | ✅ | 源。**审稿在这里定稿** |
| `_配音清单.json` | ✅ | 成本与实测时长凭据，体积极小 |
| `_出图体检.md` | ✅ | 判读凭据 |
| `frames\` `audio\` `*.mp4` `sub.srt` `_时间轴.json` `*-旁白稿.md` | ❌ | 全是产物，可重跑得出 |

`_备课视频工作区\`（外部终稿）、`工具\ffmpeg\` 整目录 gitignore。

## 交付边界

加盟商拿到的是 **mp4 + 使用说明**，不装环境、不接触详案全文——同
`writing-correction-tool-0818` 那条「总部离线出成品、加盟商端只消费」的架构。

对外件的三条内容红线（写进判据、机检会抓）：
- 禁把 `参考：` 里的学生答案讲成标准答案
- 禁出现具体学生姓名、内部称谓
- **禁替总部承诺**师训安排、班型、课时费、效果数据 —— 仓内对这些的现行口径是
  「还在定」，旁白里一个字都不要提

成片右下角固定水印「内部备课使用 · 请勿外传」。教材插图页照常出图（内部备课用）。
