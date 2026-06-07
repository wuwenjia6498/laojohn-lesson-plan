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
- 单值字段：眉标、标题、副标题、正文（可多行）、配图建议
- 列表字段：要点（以 `- ` 或 `• ` 开头）
- 表格字段：`表格：` 之后跟标准 GFM 表格

页型集合（6 种）：
    封面 / 环节标题 / 引导问题 / 原文齐读 / 要点小结 / 填空表格
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional


PAGE_TYPES = {"封面", "环节标题", "引导问题", "原文齐读", "要点小结", "填空表格"}

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
    table_headers: List[str] = field(default_factory=list)
    table_rows: List[List[str]] = field(default_factory=list)
    image_suggestion: str = ""
    course: str = ""           # 课时（如有）


@dataclass
class Deck:
    title: str = ""            # 书名
    course: str = ""           # 课时（如"导读课"）
    author: str = ""           # 作者
    grade: str = ""            # 年级
    pages: List[Page] = field(default_factory=list)


def parse_table(lines: List[str]) -> (List[str], List[List[str]]):
    """解析 GFM 风格的 markdown 表格。返回 headers, rows。"""
    headers = []
    rows = []
    table_lines = [ln for ln in lines if ln.strip().startswith("|")]
    if not table_lines:
        return headers, rows

    def split_row(line: str) -> List[str]:
        # 去掉首尾 |
        cells = line.strip().strip("|").split("|")
        return [c.strip() for c in cells]

    headers = split_row(table_lines[0])
    # 第二行是分隔线 |---|---|，跳过
    body_start = 2 if len(table_lines) > 1 and re.match(r"\|?\s*:?-+", table_lines[1].strip()) else 1
    for ln in table_lines[body_start:]:
        rows.append(split_row(ln))
    return headers, rows


def parse_md(md_text: str) -> Deck:
    deck = Deck()
    lines = md_text.splitlines()

    # 第一阶段：扫元信息（可选 YAML front-matter 风格也行；这里用简单 key: value）
    i = 0
    meta_pattern = re.compile(r"^(书名|课时|作者|年级)\s*[:：]\s*(.+?)\s*$")
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
        i += 1

    # 第二阶段：扫分页
    current: Optional[Page] = None
    pending_field: Optional[str] = None    # 正在收集多行的字段名（正文 / 表格）
    field_buf: List[str] = []
    pending_table_lines: List[str] = []

    def flush_field():
        nonlocal pending_field, field_buf, pending_table_lines
        if current is None:
            return
        if pending_field == "正文":
            current.body = "\n".join(field_buf).strip()
        elif pending_field == "表格":
            headers, rows = parse_table(pending_table_lines)
            current.table_headers = headers
            current.table_rows = rows
        pending_field = None
        field_buf = []
        pending_table_lines = []

    field_single = {"眉标", "标题", "副标题", "配图建议"}

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
        m_field = re.match(r"^(眉标|标题|副标题|正文|要点|表格|配图建议)\s*[:：]\s*(.*)$", stripped)
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
                    current.image_suggestion = tail.strip()
            elif key == "正文":
                pending_field = "正文"
                if tail.strip():
                    field_buf.append(tail)
            elif key == "要点":
                # 要点可能是单行/逗号分隔 / 也可能是后续 - 开头的列表
                if tail.strip():
                    parts = re.split(r"\s*[/／、,，]\s*", tail.strip())
                    current.bullets.extend([p for p in parts if p])
                pending_field = "要点"
            elif key == "表格":
                pending_field = "表格"
            i += 1
            continue

        # 当前在收集字段
        if pending_field == "正文":
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
            if stripped.startswith(("- ", "• ", "* ")):
                current.bullets.append(stripped[2:].strip())
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
