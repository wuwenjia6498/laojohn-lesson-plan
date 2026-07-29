# -*- coding: utf-8 -*-
"""详案 docx 首页版式化（分区提纲页 · 2026-07-22 两线统一定稿）。

样式源（按 profile 各有一份定稿样张，版式同构、行名与分区各异）：
  - picture（看图写话）＝《新_课案提纲页.docx》：三区（本课定位／本课要点／与校内的关系）。
  - writing（同步习作）＝**无区头单表 6 行**（2026-07-29 用户按《三上-猜猜他是谁》首页定稿，
    替代 2026-07-22 的两区版；区头解析仍保留，存量两区稿重渲不退化）。
共同版式：居中两行标题区（《课名》20pt ─ 分隔线 ─ 副题 13pt 灰，**无品牌行**）→ 一张
两列表、`**N、区名**` 底纹区头行分区（底纹色按 profile 的 `palette["zone_bg"]`，缺省
灰 #EDEDED；区头可缺省，缺省即整节一张表）；无底部提示框。
配色按 profile 色板（`PROFILES[*]["palette"]`，课型差异唯一收敛处）：
  - picture＝语义灰阶（#222222/#333333/#5A5A5A）＋纯黑强调、白底标签列、无红；
    三个区头行米黄底 #F5E6C6、**值列不加粗**（`palette["value_bold"]`）——两项均
    2026-07-29 用户定版（此前区头灰 #EDEDED、值列加粗）。
  - writing＝标题/副题/抬头/标签/值列一律深灰 #3F3F3F，**只有「（本课）」那一个箭头
    节点标红 #C00000**；标签列米黄底 #F5E6C6（字仍深灰、加粗），**值列不加粗**
    （`palette["value_bold"]`）；表上方另起左对齐抬头「教学提纲」（2026-07-29 用户定版）。

用法：
    PYTHONUTF8=1 python style_front_page.py <详案.md> <目标.docx> [<目标2.docx> ...]
    # profile 由 H1 自动判型；也可显式指定：--profile picture|writing

职责：
  1) 从详案 .md 解析首页数据（H1 标题、`## 教案提纲表` 下的分区表）；
  2) 打开共享引擎已产出的 docx（无图版或配图版均可），删除其开头的朴素首页块
     （H1 至第一个「第N课时」分页标题之前的全部元素）；
  3) 重建定稿版式首页并给「第N课时」锚段补分页，首页独占一页。

只做首页重排，不碰正文、页眉、图位；不修改共享 docx 引擎。样式常量以本文件为单一源。

**本文件是看图写话与同步习作两条线共用的单一源（禁 fork）**：课型差异全部收敛在
下方 `PROFILES` 表里（H1 判型、副标题来源、表宽、值列渲染规则），渲染原语课型无关。
新增课型＝加一条 profile，绝不复制本文件。
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

# ---- 分区版样式常量（照抄两份定稿样张实测值，2026-07-22；两线共用） ----
FONT = "宋体"
SEP = "　│　"         # 全角分隔
P_INK = "222222"      # 主色（标题/标签/要点强调）
P_TXT = "333333"      # 正文色
P_MUT = "5A5A5A"      # 弱化灰（副题/线名/括注/分隔符/尾注）
P_EMPH = "000000"     # 纯黑次强调（课型/本课名/提升点类型）
P_BORDER = "9A9A9A"   # 表格边框 / 标题区分隔线
P_ZONE_BG = "EDEDED"  # 区头行底纹缺省值（palette 未给 zone_bg 时回落；标签列无底纹）
P_RED = "C00000"      # 本课红标（writing 档 2026-07-29 起用；picture 档仍无红）
P_LABEL_BG = "F5E6C6" # 标签列米黄底（writing 档）
P_GREY = "3F3F3F"     # writing 档通用深灰（标题/副题/标签/值列，除本课红标外全用它）


# ======================= profile 表（课型差异唯一收敛处） =======================
# 字段说明：
#   h1        H1 正则，group(1)=H1 标题（展示标题只取其中《…》段）
#   subtitle  副标题来源：('row', 行名, 取前 N 段) | ('line', H1 下一非空行)
#             | ('h6', 期次副标正则, 0)——取该正则的 group(1)
#   detect    判型正则（可选，缺省用 h1）
#   zones_anchor  `## 教案提纲表` 锚正则，其后逐个 `**N、…**` 区头+两列表；
#             **区头可整体缺省**（writing 自 2026-07-29 起即无区头单表），此时整节作
#             一个匿名区渲染、不出灰底行。（区头只写区名；`—— 副题` 已于 2026-07-25
#             去掉，zone_row 的 dash 分支保留作向后兼容）
#   tbl       (表总宽 dxa, 标签列宽 dxa)
#   rules     行名 → 值列渲染规则名（p_* 系，见 _render_value）；未列出的行走 'plain'
PROFILES = {
    "picture": {
        # 2026-07-25 标题体例改版：H1＝课程主题式总标题（无台账字眼、无《》），
        # 台账信息移到紧跟的六级标题「期次副标」，判型与副题都取那一行。
        "detect": r"^######\s*.+?·\s*看图写话详案\s*$",
        "h1": r"^#\s+(?!#)(.+?)\s*$",
        "subtitle": ("h6", r"^######\s*(.+?)\s*·\s*看图写话详案\s*$", 0),
        "zones_anchor": r"^##\s*教案提纲表",
        "tbl": (9072, 1900),
        # 色板：ink 主色 / txt 正文 / mut 弱化 / key 次强调（课型·文体段）/ emph 本课标记
        "palette": {"ink": P_INK, "txt": P_TXT, "mut": P_MUT, "key": P_EMPH,
                    "emph": P_EMPH, "label_bg": "FFFFFF", "label_fg": P_INK,
                    "value_bold": False, "zone_bg": P_LABEL_BG},
        "caption": None,          # 表上方左对齐抬头；None＝不出
        "rules": {
            "课次·课型": "p_course",
            "学期主题": "p_dash",
            "能力线": "p_ability",
            "教学内容": "p_body_em",
            "学习目标": "p_body_em",
            "教学准备": "p_body_em",
            "对应教材": "p_tail_note",
            "校内学情起点": "p_text",
            "本课提升点": "p_delta",
            "教学边界": "p_dash_mut",
        },
    },
    "writing": {
        "h1": r"^#\s+(.+?)\s*·\s*写作课教学设计\s*$",
        "subtitle": ("line", None, 0),
        "zones_anchor": r"^##\s*(?:一、)?\s*教案提纲表",
        "tbl": (9572, 1877),
        # 2026-07-29 用户定版：标题/副题/抬头/标签/值列一律深灰 #3F3F3F，
        # 只有「（本课）」那一个箭头节点红 #C00000；标签列米黄底；值列不加粗
        "palette": {"ink": P_GREY, "txt": P_GREY, "mut": P_GREY, "key": P_GREY,
                    "emph": P_RED, "label_bg": P_LABEL_BG, "label_fg": P_GREY,
                    "value_bold": False},
        "caption": "教学提纲",
        "rules": {
            "课题·课时": "p_course",
            "能力阶段": "p_ability",
            "同类习作顺序": "p_ability",
            "教材要求": "p_src_lead",
            "学习目标": "p_body_em",
            "核心技法": "p_body_em",
            # ↓ 2026-07-29 单表改版前的旧行名，只为存量两区稿重渲不退化保留；新稿禁用
            "文体线": "p_ability",
            "核心能力点": "p_src_lead",
            "怎么落地": "p_body_em",
        },
    },
}


def detect_profile(text: str) -> str:
    for name, prof in PROFILES.items():
        if re.search(prof.get("detect", prof["h1"]), text, re.M):
            return name
    raise SystemExit("无法判型：H1 既不匹配「· 看图写话详案」也不匹配「· 写作课教学设计」")


# ---------- md 解析 ----------
def parse_md(md_path: Path, profile: str = None):
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    profile = profile or detect_profile(text)
    prof = PROFILES[profile]

    m = re.search(prof["h1"], text, re.M)
    if not m:
        raise SystemExit(f"未找到匹配 profile「{profile}」的 H1")
    title = m.group(1).strip()

    def subtitle_from(rows_all):
        kind, key, n = prof["subtitle"]
        if kind == "h6":
            m6 = re.search(key, text, re.M)
            if not m6:
                raise SystemExit("未找到期次副标行（`###### … · 看图写话详案`）")
            return m6.group(1).strip()
        if kind == "row":
            kv = dict(rows_all)
            raw = kv.get(key, "")
            parts = [p.strip() for p in re.split(r"[│|]", raw) if p.strip()]
            return " · ".join(parts[:n]) if parts else raw
        # 'line'：H1 之后第一行非空正文
        h1_i = next(i for i, l in enumerate(lines) if re.match(prof["h1"], l))
        for l in lines[h1_i + 1:]:
            s = l.strip()
            if s and not s.startswith("#"):
                return s
        return ""

    # `## 教案提纲表` 之后逐个解析 `**N、…**` 区头 + 紧随的两列表，直到下个 `##`
    idx = next((i for i, l in enumerate(lines)
                if re.search(prof["zones_anchor"], l)), None)
    if idx is None:
        raise SystemExit(f"未找到锚：{prof['zones_anchor']}")
    zones = []          # [(区头正文 or None, [(label, value), ...]), ...]
    cur_header, cur_rows, started = None, [], False   # 无区头单表：cur_header 恒为 None
    for l in lines[idx + 1:]:
        s = l.strip()
        if s.startswith("## ") or s == "---":
            break
        m_h = re.match(r"^\*\*(.+?)\*\*$", s)
        if m_h:
            if started:
                zones.append((cur_header, cur_rows))
            cur_header, cur_rows, started = m_h.group(1).strip(), [], True
        elif s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) >= 2 and not set(cells[0]) <= {"-", " ", ":"}:
                cur_rows.append((cells[0], cells[1]))
                started = True
    if started:
        zones.append((cur_header, cur_rows))
    if not zones or any(not rows for _, rows in zones):
        raise SystemExit("提纲表解析不完整（区头版：每个 **N、…** 区头后须紧跟两列表；"
                         "单表版：`## 教案提纲表` 后须紧跟一张两列表）")
    all_rows = [rv for _, rows in zones for rv in rows]
    # 展示标题＝H1 里的《…》段（含书名号）；副题走 subtitle 机制
    m_t = re.search(r"《.+?》", title)
    disp_title = m_t.group(0) if m_t else title
    return profile, disp_title, subtitle_from(all_rows), zones


# ---------- docx 低层小件（课型无关） ----------
def _set_font(run, size, bold=False, color=P_INK):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), FONT)
    rfonts.set(qn("w:hAnsi"), FONT)
    rfonts.set(qn("w:eastAsia"), FONT)


def _cell_bg(cell, hexval):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), hexval)
    tcpr.append(shd)


def _cell_width(cell, dxa):
    tcpr = cell._tc.get_or_add_tcPr()
    tcw = OxmlElement("w:tcW")
    tcw.set(qn("w:w"), str(dxa))
    tcw.set(qn("w:type"), "dxa")
    tcpr.append(tcw)


def _tbl_borders(tbl, spec):
    """spec: dict side -> (val, color, sz)；side ∈ top/left/bottom/right/insideH/insideV"""
    tblpr = tbl._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for side, (val, color, sz) in spec.items():
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), val)
        el.set(qn("w:color"), color)
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:space"), "0")
        borders.append(el)
    tblpr.append(borders)


def _tbl_fixed_width(tbl, dxa):
    tblpr = tbl._tbl.tblPr
    tblw = OxmlElement("w:tblW")
    tblw.set(qn("w:w"), str(dxa))
    tblw.set(qn("w:type"), "dxa")
    tblpr.append(tblw)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblpr.append(layout)


def _tbl_grid(tbl, widths):
    """显式改写 tblGrid 列宽（dxa）——python-docx 默认均分，样张按标签/值列定宽。"""
    grid = tbl._tbl.find(qn("w:tblGrid"))
    for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(w))


def _tbl_cell_margins(tbl, top=0, left=108, bottom=0, right=108):
    """表级单元格边距（dxa）。zones3 版照抄样张：上下 0、左右 108。"""
    tblpr = tbl._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, val in (("top", top), ("left", left),
                      ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblpr.append(mar)


def _cell_text(cell, text, size, bold, color, space=3, center=False):
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(space)
    p.paragraph_format.space_after = Pt(space)
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    _set_font(run, size, bold, color)
    return p


def _cell_valign_center(cell):
    tcpr = cell._tc.get_or_add_tcPr()
    va = OxmlElement("w:vAlign")
    va.set(qn("w:val"), "center")
    tcpr.append(va)


def _p_rule(p, side="bottom", color=P_BORDER, sz=4):
    """段落边框横线（标题区分隔线）：side ∈ top/bottom。"""
    ppr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    el = OxmlElement(f"w:{side}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:color"), color)
    el.set(qn("w:sz"), str(sz))
    el.set(qn("w:space"), "6")
    pbdr.append(el)
    ppr.append(pbdr)


# ---------- 值列富文本渲染（规则按 profile 选，实现共享） ----------
def _render_value(cell, label, value, current_key, rules, pal, space=3):
    """按 profile 的行名→规则表定制值列样式（p_* 系，全加粗）；配色取 profile 色板
    （picture＝语义灰阶＋纯黑强调；writing＝全黑＋「（本课）」红标）。
    值里的 <br> 一律渲染成真换行（与共享 docx 引擎口径一致）。
    """
    INK, TXT, MUT = pal["ink"], pal["txt"], pal["mut"]
    KEY, EMPH = pal["key"], pal["emph"]
    B = pal.get("value_bold", True)      # 值列粗细（writing 档不加粗）
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(space)
    p.paragraph_format.space_after = Pt(space)

    def run(text, size=11, bold=B, color=TXT):
        """写一段；<br> 转真换行。"""
        chunks = re.split(r"<br\s*/?>", text)
        for i, chunk in enumerate(chunks):
            r = p.add_run(chunk)
            _set_font(r, size, bold, color)
            if i < len(chunks) - 1:
                r.add_break()

    rule = rules.get(label, "plain")

    # ---- p_* 规则（全加粗；具体色值由 profile 色板决定，见文件头） ----
    if rule == "p_course":
        # 分段：段1 主色，段2（课型/文体）纯黑强调，段3 起（课时等次要信息）弱化灰；
        # 分隔符弱化灰；12pt
        parts = [s.strip() for s in re.split(r"[│|]", value) if s.strip()]
        for i, seg in enumerate(parts):
            if i:
                run(SEP, 12, B, MUT)
            run(seg, 12, B, KEY if i == 1 else (MUT if i >= 2 else INK))
    elif rule == "p_dash":
        head, dash, tail = value.partition("——")
        run(head, 11, B, INK)
        if dash:
            run(dash + tail, 11, B, TXT)
    elif rule == "p_dash_mut":
        head, dash, tail = value.partition("——")
        run(head, 11, B, INK)
        if dash:
            run(dash + tail, 11, B, MUT)
    elif rule == "p_ability":
        # 「X线：」弱化灰；本课那一个箭头节点整段升 EMPH（writing＝红、picture＝纯黑）；
        # 其余正文色。节点＝相邻两个「→」之间的整段（并列项如「我有一个想法／写日记（本课）」
        # 一并标记，与用户 2026-07-29 定版样张一致）。
        head, colon, rest = value.partition("：")
        if colon:
            run(head + colon, 11, B, MUT)
        else:
            rest = value
        key = ""
        for node in re.split(r"→", rest):          # 优先按「（本课）」标记定位整节点
            if "（本课）" in node:
                key = node.strip()
                break
        if not key:                                 # 无标记时退回按 H1 题目匹配
            key = current_key or ""
            if key and key not in rest and "：" in key:
                key = key.split("：", 1)[1]
        if key and key in rest:
            pre, post = rest.split(key, 1)
            run(pre, 11, B, TXT)
            run(key, 11, B, EMPH)
            run(post, 11, B, TXT)
        else:
            run(rest, 11, B, TXT)
    elif rule == "p_body_em":
        # 正文色为底，md `**…**` 段升主色强调
        for i, chunk in enumerate(re.split(r"\*\*(.+?)\*\*", value)):
            if chunk:
                run(chunk, 11, B, INK if i % 2 else TXT)
    elif rule == "p_tail_note":
        m = re.match(r"^(.*?)(（[^（）]*）)?\s*$", value)
        head = (m.group(1) if m else value).strip()
        note = (m.group(2) or "") if m else ""
        run(head, 11, B, INK)
        if note:
            run(note, 11, B, MUT)
    elif rule == "p_text":
        run(value, 11, B, TXT)
    elif rule == "p_ink":
        run(value, 11, B, INK)
    elif rule == "p_src_lead":
        # 「统编<册>·第N单元习作：」来源前缀弱化灰，其后的教材要求正文主色
        # （兼容存量的「对齐统编…——…」写法：先试破折号，再试全角冒号）
        for sep in ("——", "："):
            head, hit, tail = value.partition(sep)
            if hit:
                run(head + hit, 11, B, MUT)
                run(tail, 11, B, INK)
                break
        else:
            run(value, 11, B, INK)
    elif rule == "p_delta":
        m = re.match(r"^([^（：]+)(.*)$", value)
        if m:
            run(m.group(1).strip(), 11, B, KEY)
            if m.group(2):
                run(m.group(2), 11, B, TXT)
        else:
            run(value, 11, B, TXT)
    else:  # plain
        run(value, 11, B, TXT)
    return p


# ---------- 首页构建 ----------
def build_front(doc, data):
    """分区提纲页（两线共用；样张见文件头）：
    居中两行标题区（《课名》20pt ─ 分隔线 ─ 副题 13pt 灰）
    → 一张两列表（宽度按 profile），`**N、区名**` 灰底区头行分区 + 数据行；
    md 侧无区头时（writing 单表版）整表只有数据行、不出灰底行。
    表上方可带左对齐抬头（profile 的 caption）。无品牌行、无底部提示框。"""
    profile, title, subtitle, zones = data
    prof = PROFILES[profile]
    pal = prof["palette"]
    tbl_w, label_w = prof["tbl"]
    blocks = []

    def para(text, size, bold, color, before=0, after=6, center=True):
        p = doc.add_paragraph()
        if center:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(before)
        p.paragraph_format.space_after = Pt(after)
        _set_font(p.add_run(text), size, bold, color)
        blocks.append(p._p)
        return p

    current_key = ""
    m = re.search(r"《(.+?)》", title)
    if m:
        current_key = m.group(1)

    para(title, 20, True, pal["ink"], before=6, after=4)
    p_sub = para(subtitle, 13, True, pal["mut"], after=14)
    _p_rule(p_sub, side="top", color=P_BORDER, sz=12)  # 分隔线：主标题与副题之间
    if prof.get("caption"):        # 表上方左对齐抬头（writing＝「教学提纲」）
        para(prof["caption"], 11.5, True, pal["ink"], after=4, center=False)

    n_rows = sum((1 if header else 0) + len(rows) for header, rows in zones)
    tbl = doc.add_table(rows=n_rows, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    _tbl_fixed_width(tbl, tbl_w)
    _tbl_borders(tbl, {s: ("single", P_BORDER, 4) for s in
                       ("top", "left", "bottom", "right", "insideH", "insideV")})
    _tbl_cell_margins(tbl)
    _tbl_grid(tbl, (label_w, tbl_w - label_w))

    def zone_row(ri, header):
        row = tbl.rows[ri]
        row.cells[0].merge(row.cells[1])
        cell = row.cells[0]
        _cell_bg(cell, pal.get("zone_bg", P_ZONE_BG))
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        head, dash, tail = header.partition("——")
        _set_font(p.add_run(head.strip()), 11, True, pal["ink"])
        if dash:
            _set_font(p.add_run("　—— " + tail.strip()), 11, True, pal["mut"])

    def data_row(ri, label, value):
        c0, c1 = tbl.rows[ri].cells
        _cell_width(c0, label_w)
        _cell_width(c1, tbl_w - label_w)
        _cell_bg(c0, pal["label_bg"])
        _cell_bg(c1, "FFFFFF")
        _cell_text(c0, label, 11.5, True, pal["label_fg"], center=True)
        _cell_valign_center(c0)
        _cell_valign_center(c1)
        _render_value(c1, label, value, current_key, prof["rules"], pal)

    ri = 0
    for header, rows in zones:
        if header:
            zone_row(ri, header); ri += 1
        for label, value in rows:
            data_row(ri, label, value); ri += 1
    blocks.append(tbl._tbl)
    return blocks


def restyle(md_path: Path, docx_path: Path, profile: str = None):
    data = parse_md(md_path, profile)
    doc = Document(str(docx_path))
    body = doc.element.body

    # 找 anchor：第一个以「第N课时」开头的段
    anchor = None
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            texts = child.findall(qn("w:r") + "/" + qn("w:t"))
            txt = "".join(t.text or "" for t in texts).strip()
            if re.match(r"^第\s*\d+\s*课时", txt):
                anchor = child
                break
    if anchor is None:
        raise SystemExit(f"{docx_path.name}: 未找到「第N课时」锚段，放弃重排")

    # 删除 anchor 之前的全部块（旧首页）
    removed = 0
    for child in list(body.iterchildren()):
        if child is anchor:
            break
        if child.tag in (qn("w:p"), qn("w:tbl")):
            body.remove(child)
            removed += 1

    # 构建新首页（先 append 到文末，再整体搬到 anchor 前）
    blocks = build_front(doc, data)
    for el in blocks:
        anchor.addprevious(el)

    # 首页独占一页：给「第N课时」锚段补段前分页（重排可能吞掉引擎原有的分页衔接）
    ppr = anchor.find(qn("w:pPr"))
    if ppr is None:
        ppr = OxmlElement("w:pPr")
        anchor.insert(0, ppr)
    if ppr.find(qn("w:pageBreakBefore")) is None:
        ppr.append(OxmlElement("w:pageBreakBefore"))

    doc.save(str(docx_path))
    print(f"首页版式化完成[{data[0]}]：{docx_path.name}"
          f"（删旧块 {removed}，插新块 {len(blocks)}）")


def main():
    argv = sys.argv[1:]
    profile = None
    if "--profile" in argv:
        i = argv.index("--profile")
        profile = argv[i + 1]
        if profile not in PROFILES:
            raise SystemExit(f"未知 profile：{profile}（可选：{'/'.join(PROFILES)}）")
        del argv[i:i + 2]
    if len(argv) < 2:
        raise SystemExit(__doc__)
    md_path = Path(argv[0])
    for target in argv[1:]:
        restyle(md_path, Path(target), profile)


if __name__ == "__main__":
    main()
