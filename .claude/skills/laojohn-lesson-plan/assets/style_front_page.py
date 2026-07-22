# -*- coding: utf-8 -*-
"""详案 docx 首页版式化（样式源＝用户提供《详案首页示例.docx》，2026-07-21 拍板）。

用法：
    PYTHONUTF8=1 python style_front_page.py <详案.md> <目标.docx> [<目标2.docx> ...]
    # profile 由 H1 自动判型；也可显式指定：--profile picture|writing

职责：
  1) 从详案 .md 解析首页数据（H1 标题、两区表、可选的底部提示注）；
  2) 打开共享引擎已产出的 docx（无图版或配图版均可），删除其开头的朴素首页块
     （H1 至第一个「第N课时」分页标题之前的全部元素）；
  3) 重建示例版式首页：居中三行标题区 → 节标题 → 两区分组表 → 可选提示框。

只做首页重排，不碰正文、页眉、图位；不修改共享 docx 引擎。样式常量以本文件为单一源。

**本文件是看图写话与同步习作两条线共用的单一源（禁 fork）**：课型差异全部收敛在
下方 `PROFILES` 表里（H1 判型、品牌行、两区锚与区名、值列渲染规则、底部提示框），
渲染原语与版式常量课型无关。新增课型＝加一条 profile，绝不复制本文件。
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

# ---- 样式常量（照抄示例 docx 实测值 + 2026-07-21 截图定稿；课型无关） ----
NAVY = "1F3A5F"      # 深蓝：标题/标签
GRAY = "5A5A5A"      # 副题灰 / 括号注
BODY = "222222"      # 表格正文
RED = "C00000"       # 关键词强调红（课型/本期训练点/增量词/当前篇）
NOTE_BODY = "333333"  # 提示框正文
BORDER = "4E8FA6"    # 表格边框 / 提示框左色条
GROUP_BG = "E4EEF2"  # 组头底纹
LABEL_BG = "EAF1F4"  # 标签列底纹
NOTE_BG = "F4F7F8"   # 提示框底纹
NOTE_BORDER = "DDE6EA"  # 提示框细边
RULE = "D9D9D9"      # 标题区细分隔线
FONT = "宋体"
TABLE_W = 9386       # dxa
COL_LABEL_W = 1760
COL_VALUE_W = TABLE_W - COL_LABEL_W
NOTE_W = 9072
SEP = "　│　"        # 全角分隔


# ======================= profile 表（课型差异唯一收敛处） =======================
# 字段说明：
#   h1        H1 正则，group(1)=标题区主标题
#   brand     品牌行文案
#   subtitle  副标题来源：('row', 行名, 取前 N 段) | ('line', H1 下一非空行)
#   sec_title 「提纲表」节标题文案
#   zone1/2   (区名, md 锚正则)
#   rules     行名 → 值列渲染规则名；未列出的行走 'plain'
#   note      (锚正则, 提示框标签) 或 None（无底部提示框）
PROFILES = {
    "picture": {
        "h1": r"^#\s+(.+?)\s*·\s*看图写话详案\s*$",
        "brand": "老约翰 · 看图写话 24 期方法主线",
        "subtitle": ("row", "课次·课型", 2),
        "sec_title": "本课提纲表",
        "zone1": ("本课要点", r"^##\s*教案提纲表"),
        "zone2": ("这一课在整个课程里的位置", r"^\*\*这一课在整个课程里的位置\*\*"),
        "rules": {
            "课次·课型": "segs_2nd_red",
            "这一期": "head_note",
            "本学期主题": "bold",
            "能力线": "highlight_current",
            "对齐统编": "segs_delta",
        },
        "note": (r"^>\s*校内基线：(.+)$", "校内基线"),
    },
    "writing": {
        "h1": r"^#\s+(.+?)\s*·\s*写作课教学设计\s*$",
        "brand": "老约翰 · 同步习作 · 三至六年级 63 任务",
        "subtitle": ("line", None, 0),
        "sec_title": "本课提纲表",
        "zone1": ("本课要点", r"^##\s*(?:一、)?\s*教案提纲表"),
        "zone2": ("这一课在整个课程里的位置", r"^\*\*这一课在整个课程里的位置\*\*"),
        "rules": {
            "这一课": "segs_navy",
            "能力阶段": "head_note",
            "文体线": "highlight_current",
            "对齐统编": "segs_bold",
        },
        "note": None,
    },
}


def detect_profile(text: str) -> str:
    for name, prof in PROFILES.items():
        if re.search(prof["h1"], text, re.M):
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

    def read_table(after_pat):
        """返回 after_pat 之后第一个 md 两列表的 [(label, value), ...]（含首行）。"""
        idx = None
        for i, l in enumerate(lines):
            if re.search(after_pat, l):
                idx = i
                break
        if idx is None:
            raise SystemExit(f"未找到锚：{after_pat}")
        rows = []
        started = False
        for l in lines[idx + 1:]:
            s = l.strip()
            if s.startswith("|"):
                started = True
                cells = [c.strip() for c in s.strip("|").split("|")]
                if len(cells) >= 2 and not set(cells[0]) <= {"-", " ", ":"}:
                    rows.append((cells[0], cells[1]))
            elif started:
                break
        if not rows:
            raise SystemExit(f"锚 {after_pat} 后未解析到表格")
        return rows

    tbl_main = read_table(prof["zone1"][1])
    tbl_pos = read_table(prof["zone2"][1])

    # 底部提示注（可选）
    baseline = None
    if prof["note"]:
        m2 = re.search(prof["note"][0], text, re.M)
        if not m2:
            raise SystemExit(f"未找到底部提示注：{prof['note'][0]}")
        baseline = m2.group(1).strip()

    # 副标题
    kind, key, n = prof["subtitle"]
    if kind == "row":
        kv = dict(tbl_main)
        raw = kv.get(key, "")
        parts = [p.strip() for p in re.split(r"[│|]", raw) if p.strip()]
        subtitle = " · ".join(parts[:n]) if parts else raw
    else:  # 'line'：H1 之后第一行非空正文
        subtitle = ""
        h1_i = next(i for i, l in enumerate(lines) if re.match(prof["h1"], l))
        for l in lines[h1_i + 1:]:
            s = l.strip()
            if s and not s.startswith("#"):
                subtitle = s
                break
    return profile, title, subtitle, tbl_main, tbl_pos, baseline


# ---------- docx 低层小件（课型无关） ----------
def _set_font(run, size, bold=False, color=BODY):
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


def _p_rule(p, side="bottom", color=RULE, sz=4):
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


def _p_left_bar(p, color=NAVY, sz=24):
    """段落左侧粗竖条（节标题装饰）。"""
    ppr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    el = OxmlElement("w:left")
    el.set(qn("w:val"), "single")
    el.set(qn("w:color"), color)
    el.set(qn("w:sz"), str(sz))
    el.set(qn("w:space"), "4")
    pbdr.append(el)
    ppr.append(pbdr)


# ---------- 值列富文本渲染（规则按 profile 选，实现共享） ----------
def _render_value(cell, label, value, current_key, rules, space=3):
    """按 profile 的行名→规则表定制值列样式。

    规则：segs_2nd_red（分段·第2段红）／segs_navy（分段·全深蓝）／segs_bold（分段·加粗）
          segs_delta（分段·「增量：」后标红）／head_note（正文＋括号灰注）
          bold（整行加粗）／highlight_current（当前篇/期名标红）／plain（默认）
    值里的 <br> 一律渲染成真换行（与共享 docx 引擎口径一致）。
    """
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(space)
    p.paragraph_format.space_after = Pt(space)

    def run(text, size=11.5, bold=False, color=BODY):
        """写一段；<br> 转真换行。"""
        chunks = re.split(r"<br\s*/?>", text)
        for i, chunk in enumerate(chunks):
            r = p.add_run(chunk)
            _set_font(r, size, bold, color)
            if i < len(chunks) - 1:
                r.add_break()

    rule = rules.get(label, "plain")

    if rule in ("segs_2nd_red", "segs_navy", "segs_bold"):
        parts = [s.strip() for s in re.split(r"[│|]", value) if s.strip()]
        size = 12 if rule == "segs_2nd_red" else 11.5
        for i, seg in enumerate(parts):
            if i:
                run(SEP, size, False, GRAY)
            if rule == "segs_2nd_red":
                run(seg, size, True, RED if i == 1 else NAVY)
            elif rule == "segs_navy":
                run(seg, size, True, NAVY)
            else:
                run(seg, size, True, BODY)
    elif rule == "head_note":
        m = re.match(r"^(.*?)(（.*）)?\s*$", value)
        head = (m.group(1) if m else value).strip()
        note = (m.group(2) or "") if m else ""
        run(head, 11.5, True, NAVY)
        if note:
            run("　" + note.strip(), 10.5, False, GRAY)
    elif rule == "bold":
        run(value, 11.5, True, BODY)
    elif rule == "highlight_current":
        key = current_key
        if key and key not in value and "：" in key:
            key = key.split("：", 1)[1]  # 名称含副题时退化到冒号后半段
        if key and key in value:
            pre, post = value.split(key, 1)
            run(pre, 11, False, BODY)
            run(key, 11, True, RED)
            run(post, 11, False, BODY)
        else:
            run(value, 11, False, BODY)
    elif rule == "segs_delta":
        parts = [s.strip() for s in re.split(r"[│|]", value) if s.strip()]
        for i, seg in enumerate(parts):
            if i:
                run(SEP, 11.5, False, GRAY)
            m = re.match(r"^(增量：)([^（(]+)(.*)$", seg)
            if m:
                run(m.group(1), 11.5, True, BODY)
                run(m.group(2).strip(), 11.5, True, RED)
                if m.group(3):
                    run(m.group(3), 11, False, BODY)
            else:
                run(seg, 11.5, True, BODY)
    else:  # plain
        run(value, 11.5, False, BODY)
    return p


# ---------- 首页构建 ----------
def build_front(doc, data):
    profile, title, subtitle, tbl_main, tbl_pos, baseline = data
    prof = PROFILES[profile]
    blocks = []

    def para(text, size, bold, color, align=WD_ALIGN_PARAGRAPH.CENTER,
             before=0, after=6):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_before = Pt(before)
        p.paragraph_format.space_after = Pt(after)
        _set_font(p.add_run(text), size, bold, color)
        blocks.append(p._p)
        return p

    # 当前篇/期名：H1 里《》内的名字，用于「能力线／文体线」自动标红
    current_key = ""
    m = re.search(r"《(.+?)》", title)
    if m:
        current_key = m.group(1)

    para(title, 20, True, NAVY, before=6, after=4)
    para(subtitle, 13, False, GRAY, after=8)
    p_brand = para(prof["brand"], 12, True, NAVY, after=14)
    _p_rule(p_brand, side="top", color=BORDER, sz=12)  # 品牌行上方粗线（2026-07-21 定稿）
    p_sec = para(prof["sec_title"], 14, True, NAVY,
                 align=WD_ALIGN_PARAGRAPH.LEFT, after=6)
    _p_left_bar(p_sec)

    # 主表：两个组头 + 两区数据行
    n_rows = 2 + len(tbl_main) + len(tbl_pos)
    tbl = doc.add_table(rows=n_rows, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    _tbl_fixed_width(tbl, TABLE_W)
    _tbl_borders(tbl, {s: ("single", BORDER, 4) for s in
                       ("top", "left", "bottom", "right", "insideH", "insideV")})

    def group_row(ri, text):
        row = tbl.rows[ri]
        row.cells[0].merge(row.cells[1])
        cell = row.cells[0]
        _cell_bg(cell, GROUP_BG)
        _cell_text(cell, text, 11, True, NAVY)

    def data_row(ri, label, value):
        c0, c1 = tbl.rows[ri].cells
        _cell_width(c0, COL_LABEL_W)
        _cell_width(c1, COL_VALUE_W)
        _cell_bg(c0, LABEL_BG)
        _cell_bg(c1, "FFFFFF")
        _cell_text(c0, label, 11.5, True, NAVY, center=True)
        _cell_valign_center(c0)
        _cell_valign_center(c1)
        _render_value(c1, label, value, current_key, prof["rules"])

    ri = 0
    group_row(ri, prof["zone1"][0]); ri += 1
    for label, value in tbl_main:
        data_row(ri, label, value); ri += 1
    group_row(ri, prof["zone2"][0]); ri += 1
    for label, value in tbl_pos:
        data_row(ri, label, value); ri += 1
    blocks.append(tbl._tbl)

    if baseline is None:
        return blocks

    # 间隔小段
    gap = doc.add_paragraph()
    gap.paragraph_format.space_before = Pt(2)
    gap.paragraph_format.space_after = Pt(2)
    blocks.append(gap._p)

    # 底部提示框（左粗色条）
    note = doc.add_table(rows=1, cols=1)
    _tbl_fixed_width(note, NOTE_W)
    _tbl_borders(note, {
        "top": ("single", NOTE_BORDER, 2),
        "bottom": ("single", NOTE_BORDER, 2),
        "right": ("single", NOTE_BORDER, 2),
        "left": ("single", BORDER, 24),
        "insideH": ("none", "auto", 0),
        "insideV": ("none", "auto", 0),
    })
    cell = note.rows[0].cells[0]
    _cell_bg(cell, NOTE_BG)
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after = Pt(5)
    _set_font(p.add_run(prof["note"][1] + "　"), 11, True, NAVY)
    _set_font(p.add_run(baseline), 11, False, NOTE_BODY)
    blocks.append(note._tbl)
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
