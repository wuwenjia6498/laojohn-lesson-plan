---
name: promo-video-line-plan-0924
description: 家长向竖屏短视频宣传片线（laojohn-promo-video）0924 仅调研+方案、未写代码；用户已拍板的选型与可复用件
metadata:
  type: project
---

2026-09-24 立项调研，**只出方案、未建文件未写代码**。方案全文在用户目录计划文件 `validated-beaming-hopcroft.md`（不在仓内）。

用户拍板：一课次/一本书一支；画面＝静态图运镜＋AI 图生视频＋`E:\my-Workspace\_assets` 学生课堂照片（原地引用、不拷进仓，根路径配置化＋md5 钉图）；声音＝火山豆包 TTS＋本校老师声音克隆；本仓直接出 9:16 成片 mp4；素材不设限（见 [[copyright-forwarding-restriction-removed-0924]]）。

**Why:** 三条课程线都缺对家长的短视频获客物料；仓内无任何竖屏/BGM 积累。

**How to apply:**
- 复用 lesson-video 底层（`ttsclient.py`、`ffmpeg_path.py`、逐句合成零漂移时间轴、`wrap()` 避头尾）走真源+薄壳，禁复制；需改三处：`DEFAULT_INSTRUCTION` 可传参、`user.uid` 参数化、`ffmpeg_path._project_root()` 找根锚点（现靠「写作课详案输出」）。改后须回归五上四 `--sample 6`。见 [[lesson-video-line-0921]]。
- 新建：竖屏渲染（zoompan/xfade/sidechaincompress 压 BGM）、图生视频客户端（`imgclient` 无视频能力、RATIO 表也不认 9:16）、家长口吻脚本规则、声音克隆通道（加进 `ttsclient.PROVIDERS`）。
- 家长文风样本：写作海报 json 三卡、家长一页纸 json、销售沟通要点第四节。
- 实现时须补：新输出目录 `.gitignore`（现有规则锁在「写作课备课视频输出」）、CLAUDE.md §3/§5 联网例外④/§7/§8、AI 内容标识角标。
