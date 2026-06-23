#!/usr/bin/env python3
"""
laojohn-course-poster 萃取脚手架
用法:
    python3 extract_fields.py <课案.md> <输出 data.json> [--profile <书籍档案.md>]

职责边界(重要):
    本脚本只做【确定性机械抽取】——把课案里"明确字段"里能直接拿到的 A 类信息
    抽出来,并为 B 类(留占位)、C 类(AI 提炼)生成带占位文案的骨架。
    它【不做】任何理解性提炼。C 类两栏(内容简介 / 阅读收获)必须由 AI
    在生成的 JSON 骨架上手动填写,受 SKILL.md 的反编造红线约束。

    当传入 --profile 书籍档案.md 时,脚本会读取档案里 '## 海报/指南元数据' 块,
    用其中已填写的字段替换原来的 B 类占位(出版社/字数/页数/类型/主题/获奖)。
    '（待补充）' 视为缺失,仍保留占位框。
"""
import json
import re
import sys
import argparse

# ---- B 类基本信息缺失时输出空字符串 ----
# 最终物料里栏位保留、值留空白，不写"待补充/请回填"、不画占位框；绝不从正文猜、绝不编。
# （"待补充"的人工回填提示只保留在书籍档案机读块，不进对外物料。）
PLACEHOLDER = {
    "publisher": "",
    "word_count": "",
    "page_count": "",
    "book_type": "",
    "theme": "",
}
# 获奖信息缺失 → 留空,模板自动隐藏整个获奖块(列表项缺失即整条不出现,非画空框)
AWARD_PLACEHOLDER = ""

# ---- C 类占位文案(AI 必须替换,留着代表 AI 漏填,渲染会醒目提示)----
C_SUMMARY_TODO = '【内容简介待 AI 提炼：80–100 字故事梗概，只压缩课案「内容简介」段，不得新增情节】'
C_GAINS_TODO = [
    '【阅读收获待 AI 提炼第 1 条：20–35 字，概括自「情感价值/知识技能」目标】',
    '【阅读收获待 AI 提炼第 2 条：20–35 字，每条须能在课案找到依据】',
]


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---- 书籍档案元数据解析 ----

def _is_blank(val):
    """值为空或「待补充」占位时视为缺失。"""
    stripped = val.strip() if val else ""
    return not stripped or stripped in ("（待补充）", "(待补充)", "待补充", "—", "-", "教案未涵盖")


def _parse_simple_field(section, label):
    """从元数据块中按 '- label：value' 格式取单行值。"""
    m = re.search(r"^-\s*" + re.escape(label) + r"[：:](.*)$", section, re.M)
    if m:
        val = m.group(1).strip()
        return None if _is_blank(val) else val
    return None


def _parse_award_list(section):
    """从元数据块中取获奖列表（- 获奖：后的子列表项，或同行写法）。"""
    # 多行子列表写法：
    #   - 获奖：
    #     - 纽伯瑞儿童文学奖
    m = re.search(r"^-\s*获奖[：:]\s*\n((?:[ \t]+-\s*.+\n?)*)", section, re.M)
    if m:
        items = re.findall(r"^[ \t]+-\s*(.+)$", m.group(1), re.M)
        cleaned = [i.strip() for i in items if not _is_blank(i)]
        return cleaned if cleaned else None
    # 同行写法：- 获奖：xxx
    m = re.search(r"^-\s*获奖[：:](.+)$", section, re.M)
    if m:
        val = m.group(1).strip()
        return [val] if not _is_blank(val) else None
    return None


def parse_profile_metadata(profile_text):
    """从书籍档案的 '## 海报/指南元数据' 块中抽取结构化字段。
    返回 dict；字段缺失或为占位时对应 value 为 None。
    """
    sec_m = re.search(r"##\s*海报/指南元数据[^\n]*\n(.*?)(?=\n##|\Z)", profile_text, re.S)
    if not sec_m:
        return {}
    section = sec_m.group(1)
    return {
        "level":     _parse_simple_field(section, "等级"),
        "author":    _parse_simple_field(section, "作者"),
        "publisher": _parse_simple_field(section, "出版社"),
        "word_count": _parse_simple_field(section, "字数"),
        "page_count": _parse_simple_field(section, "页数"),
        "book_type": _parse_simple_field(section, "类型"),
        "theme":     _parse_simple_field(section, "主题"),
        "award":     _parse_award_list(section),
    }


def extract_title(md):
    """书名:一级标题 # 《X》... 里的书名。缺失 → 返回 None(由调用方报错停)。"""
    m = re.search(r"^#\s*《([^》]+)》", md, re.M)
    return m.group(1).strip() if m else None


def extract_level(md):
    """等级标:第二行 'Lx · ...' 的 L 数字。"""
    m = re.search(r"\bL\s*(\d+)\b", md)
    return f"L{m.group(1)}" if m else "L?"


def extract_author(md):
    """作者:'作者简介' 段首的人名(第一个逗号/句号前)。
    兼容 **【作者简介】** 包裹、段后多空行。"""
    m = re.search(r"【作者简介】\**\s*\n\s*\n?\s*([^，。,.\n、]+)", md)
    if m:
        return m.group(1).strip()
    return None


def extract_row_after(md, key):
    """从提纲表格里抽 'key | 值' 那一行的值。用于阅读策略、可视化工具。"""
    # 形如:| 三、阅读策略 | 提问、推断、比较… |
    m = re.search(r"\|[^|]*" + re.escape(key) + r"[^|]*\|\s*([^|]+?)\s*\|", md)
    if m:
        return m.group(1).strip()
    return None


def build_skeleton(md, profile_md=None):
    title = extract_title(md)
    if not title:
        sys.stderr.write(
            "✗ 致命:课案里找不到书名(应为一级标题 `# 《书名》…`)。"
            "书名是硬门槛,无法用占位代替,请检查课案。\n"
        )
        sys.exit(2)

    author = extract_author(md)
    strategies = extract_row_after(md, "阅读策略")
    vistools = extract_row_after(md, "可视化教学工具") or extract_row_after(md, "可视化")

    # 从书籍档案的 '海报/指南元数据' 块读取 B 类字段（有则替换占位，无则保留占位）
    meta = parse_profile_metadata(profile_md) if profile_md else {}
    # 作者：先用机读块「- 作者：」，回退课案「作者简介」段
    author = meta.get("author") or author
    # 等级：先用课案 L 号，抽不到再回退机读块「- 等级：」
    level = extract_level(md)
    if level == "L?":
        level = meta.get("level") or "L?"

    def b(key, placeholder_key):
        """B 类字段：优先用书籍档案值，缺失则保留占位框。"""
        val = meta.get(key)
        return val if val is not None else PLACEHOLDER[placeholder_key]

    data = {
        # —— A 类:直接抽,抽不到的非硬门槛字段也降级为占位 ——
        "title": title,
        "level": level,
        "author": f"作者：{author}" if author else "",
        "strategies": strategies or "",
        "vistools": vistools or "",
        # —— B 类:优先从书籍档案取,仍缺则留空(栏位保留、值空白) ——
        "publisher": b("publisher", "publisher"),
        "word_count": b("word_count", "word_count"),
        "page_count": b("page_count", "page_count"),
        "book_type":  b("book_type",  "book_type"),
        "theme":      b("theme",      "theme"),
        "award":      meta["award"] if meta.get("award") is not None else AWARD_PLACEHOLDER,
        # —— C 类:AI 必须替换的占位 ——
        "summary": C_SUMMARY_TODO,
        "gains": C_GAINS_TODO,
        # —— 封面:由 render 脚本按 title 去 covers/ 匹配,匹配不到用占位 ——
        # (此处不写路径,渲染时解析)
    }
    return data


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("md", help="课案详案 .md 路径")
    ap.add_argument("out_json", help="输出 data.json 路径")
    ap.add_argument(
        "--profile",
        default=None,
        help="书籍档案 .md 路径；档案内须有 '## 海报/指南元数据' 块，"
             "脚本自动读取出版社/字数/页数/类型/主题/获奖，替换 B 类占位",
    )
    args = ap.parse_args()

    md = read(args.md)
    profile_md = read(args.profile) if args.profile else None
    data = build_skeleton(md, profile_md)

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✓ 已生成骨架 JSON：{args.out_json}")
    print(f"  书名：{data['title']}  等级：{data['level']}")
    if args.profile:
        filled = [k for k in ("publisher", "word_count", "page_count", "book_type", "theme", "award")
                  if data.get(k) not in (None, AWARD_PLACEHOLDER) and "请回填" not in str(data.get(k, ""))]
        print(f"  书籍档案已填充字段：{', '.join(filled) if filled else '（无匹配字段）'}")
    print("  提醒：C 类两栏(summary / gains)仍是占位,需由 AI 按红线填实后再渲染。")
