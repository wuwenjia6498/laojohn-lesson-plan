#!/usr/bin/env python
"""书籍档案「机读块」解析 · 单一源(禁复制逻辑)

机读块 `## 海报/指南元数据` 的格式由本 skill(laojohn-book-profile)定义——键名见
`assets/book-profile-template.md`——所以解析器也由本 skill 提供:谁定义格式,谁给解析器。

使用者(CLAUDE.md §3 已登记):
    laojohn-book-card     —— scripts/extract_fields.py(出版社/字数/页数/作者)
    laojohn-course-poster —— scripts/extract_fields.py(另加类型/主题/获奖)
改本文件等于同时改两条线,须两线一并回归。

注:`extract_title` / `extract_level` 读的是**课案**而非书籍档案,不属本模块,
留在各自 extract_fields.py 里。
"""
import re

# 值命中这些标记时视为缺失(两线并集)。它们是书籍档案里给人看的回填提示,
# 按 CLAUDE.md §2「缺失留空」红线,绝不能原样进对外物料。
BLANK_MARKERS = (
    "（待补充）", "(待补充)", "待补充",
    "—", "-",
    "教案未涵盖", "未涵盖",
)


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def is_blank(val):
    """值为空或命中占位标记时视为缺失。"""
    stripped = val.strip() if val else ""
    return not stripped or stripped in BLANK_MARKERS


def meta_section(profile_md):
    """返回书籍档案 '## 海报/指南元数据' 块的原文,找不到返回空串。"""
    m = re.search(r"##\s*海报/指南元数据[^\n]*\n(.*?)(?=\n##|\Z)", profile_md, re.S)
    return m.group(1) if m else ""


def simple_field(section, label):
    """从元数据块取 '- label：value' 的单行值;缺失或占位返回 None。"""
    m = re.search(r"^-\s*" + re.escape(label) + r"[：:](.*)$", section, re.M)
    if m:
        val = m.group(1).strip()
        return None if is_blank(val) else val
    return None


def award_list(section):
    """取获奖列表;无有效项返回 None(缺失则整块隐藏,不画空框)。

    兼容两种写法:
        - 获奖：            |  - 获奖：纽伯瑞儿童文学奖
          - 纽伯瑞儿童文学奖  |
    """
    # 多行子列表写法
    m = re.search(r"^-\s*获奖[：:]\s*\n((?:[ \t]+-\s*.+\n?)*)", section, re.M)
    if m:
        items = re.findall(r"^[ \t]+-\s*(.+)$", m.group(1), re.M)
        cleaned = [i.strip() for i in items if not is_blank(i)]
        return cleaned if cleaned else None
    # 同行写法
    m = re.search(r"^-\s*获奖[：:](.+)$", section, re.M)
    if m:
        val = m.group(1).strip()
        return [val] if not is_blank(val) else None
    return None
