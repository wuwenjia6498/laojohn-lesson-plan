# -*- coding: utf-8 -*-
"""中间稿 markdown 解析。

中间稿契约：
    <可选的元信息块（Header）>
    <可选的封面信息>

    ## P01 | 页型:封面
    标题：...
    正文：...
    ...

    ## P02 | 页型:环节标题
    眉标：...
    标题：...
    正文：...

字段集合：眉标 / 标题 / 副标题 / 正文 / 要点 / 表格 / 配图建议
- 单值字段：眉标、标题、副标题、正文（可多行）
- 列表字段：要点（以 `- ` 或 `• ` 开头）
  - 某条要点(问题)下若紧跟一行 `参考：答案`，该答案挂到上一条要点，存进
    bullet_answers[i]；laojohn-ppt 把它渲成红字、问题后逐段点击淡入（见
    layouts.render_guide / render_summary）。
- 表格字段：`表格：` 之后跟标准 GFM 表格
  - 单元格内 `{{答案}}` 标记 = 该格的"填空答案"片段；底表渲成空白占位、答案做成
    叠层在 laojohn-ppt 端逐格点击淡入（见 layouts.render_table）。
- 配图建议：可重复多行；单条走单图占位，引导问题页 ≥2 条触发 2×2 四图网格
  （image_suggestion 留首条兼容旧路径，image_suggestions 收全部）

页型集合（6 种）：
    封面 / 环节标题 / 引导问题 / 原文齐读 / 要点小结 / 填空表格
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple


# 页型并集（课型无关）：原读书会 6 种 + 写作课新增「双栏对照 / 写作任务 / 情境任务 /
# 写法讲解 / 活动指令」。本集合只是"语法上允许"的全集；某页型在某 profile 下是否有效，
# 由 build_ppt 的 RENDERERS_<profile> 字典裁决（查不到 renderer 即报错）。reading profile
# 不产出写作页型即可。
PAGE_TYPES = {"封面", "环节标题", "引导问题", "原文齐读", "要点小结", "填空表格",
              "双栏对照", "写作任务", "情境任务", "写法讲解", "活动指令", "示范文",
              "实景观察",
              # 宣讲 profile（文体：宣讲）新增 8 种，同样由 RENDERERS_PROMO 裁决有效性
              "主张", "数据面板", "体系全景", "流程时间轴", "并列卡片", "图集",
              "满屏图", "收尾"}

# 表格单元格答案标记：{{答案}} —— full 取答案、blank 取占位
ANSWER_RE = re.compile(r"\{\{(.+?)\}\}")
BLANK_PLACEHOLDER = "＿＿"

# 要点列表里的"参考答案"行：紧跟某条要点之后的 `参考：答案`（可缩进，已 strip）
REF_RE = re.compile(r"^参考\s*[:：]\s*(.+?)\s*$")

# 有序要点行：`1. ` / `1、` / `1) ` 起头（区别于无序 `- `/`• `/`* `）。
# 命中即该页要点有先后次序，渲染成序号；否则圆点符号。
ORDERED_BULLET_RE = re.compile(r"^\d+\s*[.、)]\s+(.+)$")

PAGE_HEADER_RE = re.compile(
    r"^##\s*P(?P<num>\d+)\s*\|\s*页型\s*:\s*(?P<type>\S+?)\s*(?:\|\s*课时\s*:\s*(?P<course>.+?))?\s*$"
)


@dataclass
class Page:
    num: int
    page_type: str
    eyebrow: str = ""          # 眉标
    title: str = ""
    subtitle: str = ""
    body: str = ""             # 多行正文
    bullets: List[str] = field(default_factory=list)
    # 与 bullets 平行对齐：每条要点(问题)的参考答案，无答案处为 ""。
    # 来源=要点列表里紧跟某条 `- 问题` 之后的 `参考：答案` 行；
    # laojohn-ppt 把它渲成红字、问题之后逐段点击淡入（见 layouts.render_guide/summary）。
    bullet_answers: List[str] = field(default_factory=list)
    # 要点有无先后次序：无序(`- `列表)=False→渲染成圆点符号；有序(`1. `列表)=True→渲染成序号。
    # 课型无关；主要供写作课「写法讲解」按内容语义切换标记（并列要点不硬套 1/2/3）。
    bullets_ordered: bool = False
    table_headers: List[str] = field(default_factory=list)
    table_rows: List[List[str]] = field(default_factory=list)   # 存"完整答案版"（{{X}}→X）
    # 答案格：{(数据行0基, 列0基): {"blank": 占位版, "full": 完整版}}，供逐格点击叠层
    table_reveals: Dict[Tuple[int, int], dict] = field(default_factory=dict)
    image_suggestion: str = ""                                  # 单条（兼容旧逻辑/单图页）
    image_suggestions: List[str] = field(default_factory=list)  # 多条（≥2 触发四图网格）
    # 真实图片路径（相对中间稿目录或绝对路径）。来源=`配图建议：图=<路径>｜说明…` 的 图= 段。
    # 有路径→渲染端铺真图（add_image_cover）；无→退回虚线占位框。课型无关；仅写作 profile 用。
    image_path: str = ""
    course: str = ""           # 课时（如有）
    # —— 写作课页型用的通用数据字段（课型无关；reading profile 不产出即留默认空）——
    # 「双栏对照」(render_compare)：块模式用 left_body/right_body（各一大段），
    # 行模式用现有 table_headers/table_rows（2 列：句子↔批注）。模式在渲染端按内容自动判。
    left_title: str = ""       # 左栏小标题（如"改前""A：跑题"）
    left_body: str = ""        # 左栏正文（多行）
    right_title: str = ""      # 右栏小标题（如"改后""B：切题"）
    right_body: str = ""       # 右栏正文（多行）
    # 「写作任务」(render_writing_task)：把计时/字数提为显要视觉元素，不压进 bullet
    timer: str = ""            # 计时（如"约 22 分钟"）
    word_count: str = ""       # 字数指引（如"150–250 字"；详案没给则留空）
    # 「示范文」(render_model_essay) 分句上色图例：[(码, 图例名), ...]，颜色按序取调色板；
    # 正文里 `[码:片段]` 标注的片段渲染成对应色，让"哪句写颜色/声音/比喻"在文字上跳出来。
    legend: List[Tuple[str, str]] = field(default_factory=list)
    # —— v8 视觉版式选择器（写作 profile 用；不声明＝默认，向后兼容）——
    # 标题样式：""=纯文字（默认）/ "强调"=粉底圆角+红边+红短线 / "竖条"=左红竖条。
    # 来源=页内 `标题样式：强调|竖条` 行。渲染端 _heading 据此切换，纯样式、无课型分支。
    title_style: str = ""
    # 要点样式：""=竖排(默认) / "卡片" / "步骤" / "图文" / "节点"。来源=页内 `要点样式：X` 行。
    # 写法讲解/情境任务的要点渲染据此分派；未知值回退竖排。
    bullet_style: str = ""
    # 卡片版式末条红底强调（来源=`要点样式：卡片强调`）。仅卡片版式生效。
    bullets_highlight_last: bool = False
    # 「实景观察」(render_scene_observe) 用：每个场景一组 (图路径, 场景名, 问题, 答案)。
    # 来源=页内重复的 `场景：图=<路径>｜名=<场景名>｜问=<问题>｜答=<答案>` 行。
    # 1 景→单景版面(图右/图上)，2 景→双景并排。无图路径的场景仍渲染卡片骨架（图位留占位）。
    scenes: List[dict] = field(default_factory=list)
    # 演讲者备注：写进 pptx 自带的备注页（放映时只有讲者看得到，不占版面）。
    # 来源=页内 `备注：` 多行字段。课型无关——不写该字段即留空、对既有两 profile 无影响。
    notes: str = ""


@dataclass
class Deck:
    title: str = ""            # 书名
    course: str = ""           # 课时（如"导读课"）
    author: str = ""           # 作者
    grade: str = ""            # 年级
    doc_kind: str = ""         # 文体：""=读书会（缺省/向后兼容）、"写作"=写作课
    pages: List[Page] = field(default_factory=list)


def parse_table(lines: List[str]):
    """解析 GFM 风格的 markdown 表格。返回 (headers, rows, reveals)。

    rows 存"完整答案版"（{{X}}→X）；reveals 收答案格：
        {(数据行0基, 列0基): {"blank": 占位版, "full": 完整版}}。
    含 {{}} 标记的单元格即为答案格，由 laojohn-ppt 做逐格点击叠层。
    """
    headers = []
    rows = []
    reveals = {}
    table_lines = [ln for ln in lines if ln.strip().startswith("|")]
    if not table_lines:
        return headers, rows, reveals

    def split_row(line: str) -> List[str]:
        # 去掉首尾 |
        cells = line.strip().strip("|").split("|")
        return [c.strip() for c in cells]

    headers = split_row(table_lines[0])  # 表头不参与答案揭示
    # 第二行是分隔线 |---|---|，跳过
    body_start = 2 if len(table_lines) > 1 and re.match(r"\|?\s*:?-+", table_lines[1].strip()) else 1
    for d, ln in enumerate(table_lines[body_start:]):
        cells = split_row(ln)
        full_cells = []
        for c, cell in enumerate(cells):
            if ANSWER_RE.search(cell):
                full = ANSWER_RE.sub(lambda m: m.group(1), cell)
                blank = ANSWER_RE.sub(BLANK_PLACEHOLDER, cell)
                reveals[(d, c)] = {"blank": blank, "full": full}
                full_cells.append(full)
            else:
                full_cells.append(cell)
        rows.append(full_cells)
    return headers, rows, reveals


def parse_md(md_text: str) -> Deck:
    deck = Deck()
    lines = md_text.splitlines()

    # 第一阶段：扫元信息（可选 YAML front-matter 风格也行；这里用简单 key: value）
    i = 0
    meta_pattern = re.compile(r"^(书名|课时|作者|年级|文体)\s*[:：]\s*(.+?)\s*$")
    while i < len(lines):
        ln = lines[i].strip()
        if not ln:
            i += 1
            continue
        if ln.startswith("##"):
            break
        m = meta_pattern.match(ln)
        if m:
            key, val = m.group(1), m.group(2)
            if key == "书名":
                deck.title = val
            elif key == "课时":
                deck.course = val
            elif key == "作者":
                deck.author = val
            elif key == "年级":
                deck.grade = val
            elif key == "文体":
                deck.doc_kind = val
        i += 1

    # 第二阶段：扫分页
    current: Optional[Page] = None
    pending_field: Optional[str] = None    # 正在收集多行的字段名（正文 / 表格）
    field_buf: List[str] = []
    pending_table_lines: List[str] = []

    # 多行字段名 → Page 属性（正文/左正文/右正文 共用同一收集机制）
    multiline_targets = {"正文": "body", "左正文": "left_body", "右正文": "right_body",
                         "备注": "notes"}

    def flush_field():
        nonlocal pending_field, field_buf, pending_table_lines
        if current is None:
            return
        if pending_field in multiline_targets:
            setattr(current, multiline_targets[pending_field], "\n".join(field_buf).strip())
        elif pending_field == "表格":
            headers, rows, reveals = parse_table(pending_table_lines)
            current.table_headers = headers
            current.table_rows = rows
            current.table_reveals = reveals
        pending_field = None
        field_buf = []
        pending_table_lines = []

    field_single = {"眉标", "标题", "副标题", "配图建议",
                    "左标题", "右标题", "计时", "字数", "图例",
                    "标题样式", "要点样式", "场景"}

    while i < len(lines):
        raw = lines[i]
        ln = raw.rstrip()
        stripped = ln.strip()

        m_page = PAGE_HEADER_RE.match(stripped)
        if m_page:
            if current is not None:
                flush_field()
                deck.pages.append(current)
            page_type = m_page.group("type").strip()
            if page_type not in PAGE_TYPES:
                raise ValueError(f"P{m_page.group('num')} 页型未识别：{page_type}（应为 {PAGE_TYPES}）")
            current = Page(num=int(m_page.group("num")), page_type=page_type)
            if m_page.group("course"):
                current.course = m_page.group("course").strip()
            i += 1
            continue

        if current is None:
            i += 1
            continue

        # 字段头匹配："X：" 或 "X:"
        m_field = re.match(
            r"^(眉标|标题样式|标题|副标题|正文|要点样式|要点|表格|配图建议|左标题|左正文|右标题|右正文|计时|字数|图例|场景|备注)\s*[:：]\s*(.*)$",
            stripped)
        if m_field:
            # 切换字段前 flush
            flush_field()
            key = m_field.group(1)
            tail = m_field.group(2)
            if key in field_single:
                if key == "眉标":
                    current.eyebrow = tail.strip()
                elif key == "标题":
                    current.title = tail.strip()
                elif key == "副标题":
                    current.subtitle = tail.strip()
                elif key == "配图建议":
                    val = tail.strip()
                    if val:
                        # 可选真图路径：`图=<路径>｜说明…`。拆出 图= 段存 image_path，
                        # 其余段仍作占位说明文字（无图时退回虚线占位框、有图直接铺图）。
                        segs = [s.strip() for s in re.split(r"\s*[｜|]\s*", val) if s.strip()]
                        kept = []
                        for s in segs:
                            m_img = re.match(r"^图\s*[=＝]\s*(.+)$", s)
                            if m_img and not current.image_path:
                                current.image_path = m_img.group(1).strip()
                            else:
                                kept.append(s)
                        sug = "｜".join(kept) if kept else val
                        current.image_suggestions.append(sug)
                        if not current.image_suggestion:
                            current.image_suggestion = sug
                elif key == "标题样式":
                    v = tail.strip()
                    # v8.1：粉底色块是默认标题款；"强调"/"默认"=同款别名，"竖条"/"纯文字"/"无"=例外。
                    if v in {"强调", "默认", "竖条", "纯文字", "无"}:
                        current.title_style = v
                elif key == "要点样式":
                    v = tail.strip()
                    if v == "卡片强调":
                        current.bullet_style = "卡片"
                        current.bullets_highlight_last = True
                    elif v in {"竖排", "卡片", "步骤", "图文", "节点"}:
                        current.bullet_style = v
                elif key == "场景":
                    # `场景：图=<路径>｜名=<场景名>｜问=<问题>｜答=<答案>`（后三段可缺）
                    sc = {"image_path": "", "name": "", "question": "", "answer": ""}
                    for s in re.split(r"\s*[｜|]\s*", tail.strip()):
                        m_kv = re.match(r"^(图|名|问|答)\s*[=＝:：]\s*(.*)$", s.strip())
                        if not m_kv:
                            continue
                        k2, v2 = m_kv.group(1), m_kv.group(2).strip()
                        sc[{"图": "image_path", "名": "name",
                            "问": "question", "答": "answer"}[k2]] = v2
                    if any(sc.values()):
                        current.scenes.append(sc)
                elif key == "左标题":
                    current.left_title = tail.strip()
                elif key == "右标题":
                    current.right_title = tail.strip()
                elif key == "计时":
                    current.timer = tail.strip()
                elif key == "字数":
                    current.word_count = tail.strip()
                elif key == "图例":
                    # 形如 `中心=中心句｜色=看得见的颜色｜感=听到·摸到的感觉｜喻=打比方`
                    for item in re.split(r"\s*[｜|]\s*", tail.strip()):
                        if "=" in item:
                            code, name = item.split("=", 1)
                            if code.strip() and name.strip():
                                current.legend.append((code.strip(), name.strip()))
            elif key in multiline_targets:    # 正文 / 左正文 / 右正文
                pending_field = key
                if tail.strip():
                    field_buf.append(tail)
            elif key == "要点":
                # 要点可能是单行/逗号分隔 / 也可能是后续 - 开头的列表
                if tail.strip():
                    parts = re.split(r"\s*[/／、,，]\s*", tail.strip())
                    for p in parts:
                        if p:
                            current.bullets.append(p)
                            current.bullet_answers.append("")
                pending_field = "要点"
            elif key == "表格":
                pending_field = "表格"
            i += 1
            continue

        # 当前在收集字段
        if pending_field in multiline_targets:    # 正文 / 左正文 / 右正文
            if stripped == "":
                # 空行：保留为段落分隔
                field_buf.append("")
            elif stripped.startswith("##"):
                # 不应到此（已被 PAGE_HEADER_RE 捕获），稳妥起见
                continue
            else:
                field_buf.append(ln.strip())
            i += 1
            continue

        if pending_field == "要点":
            _ordered_m = ORDERED_BULLET_RE.match(stripped)
            if stripped.startswith(("- ", "• ", "* ")):
                current.bullets.append(stripped[2:].strip())
                current.bullet_answers.append("")
            elif _ordered_m:
                # 有序列表 `1. 项`：去掉序号前缀（渲染端重排），并标记该页要点有次序
                current.bullets.append(_ordered_m.group(1).strip())
                current.bullet_answers.append("")
                current.bullets_ordered = True
            elif REF_RE.match(stripped) and current.bullets:
                # `参考：答案` 行：挂到上一条要点（红字逐段点击）
                current.bullet_answers[-1] = REF_RE.match(stripped).group(1)
            elif stripped == "":
                pass
            else:
                # 视为字段结束（下一字段未显式声明的纯文本，忽略）
                pass
            i += 1
            continue

        if pending_field == "表格":
            if stripped.startswith("|"):
                pending_table_lines.append(stripped)
            elif stripped == "":
                pass
            else:
                # 表格结束
                flush_field()
            i += 1
            continue

        i += 1

    if current is not None:
        flush_field()
        deck.pages.append(current)

    return deck
