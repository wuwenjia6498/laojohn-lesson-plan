#!/usr/bin/env python3
"""
laojohn-book-card 字段萃取脚本
用法:
    python3 extract_fields.py <课案.md> <输出 data.json> --profile <书籍档案.md>

职责边界:
    本脚本只做【确定性机械抽取】。
    - A 类字段（title, level）:从课案机械抽取。
    - B 类字段（author, publisher, word_count, page_count）:优先从书籍档案取，缺失则占位。
    - C 类字段（summary）:留 AI 占位文案，必须由 AI 按课案内容提炼后填入。

    脚本绝不从课案正文口语里猜测 B 类字段，绝不联网补全，绝不凭记忆编造。
"""
import json
import re
import sys
import argparse


# ─── 缺失留空 ────────────────────────────────────────────────────────────────
# 基本信息缺失时输出空字符串：最终物料里该栏位保留、值留空白，不写"待补充/请回填"、不画占位框。
# （"待补充"的人工回填提示只保留在书籍档案机读块，不进对外物料。）

PLACEHOLDER = {
    "author":      "",
    "publisher":   "",
    "word_count":  "",
    "page_count":  "",
}
C_SUMMARY_TODO = "【内容简介待 AI 提炼：100–200 字，只压缩课案「内容简介」及「写作缘起」段，可引入具体人物/情节细节，确保信息量充实，不得新增书外信息】"


# ─── 工具函数 ─────────────────────────────────────────────────────────────────

def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _is_blank(val):
    """值为空或各类占位标记时视为缺失。"""
    stripped = val.strip() if val else ""
    return not stripped or stripped in (
        "（待补充）", "(待补充)", "待补充", "—", "-", "教案未涵盖", "未涵盖"
    )


# ─── A 类：从课案抽取 ─────────────────────────────────────────────────────────

def extract_title(md):
    """书名：一级标题里的《X》。H1 可带年级等前缀(如 # 五年级《洞》整本书教学设计)。缺失 → 报错停。"""
    m = re.search(r"^#[^《\n]*《([^》]+)》", md, re.M)
    return m.group(1).strip() if m else None


def extract_level(md):
    r"""等级标：课案里 L\d+ 模式取第一个。"""
    m = re.search(r"\bL\s*(\d+)\b", md)
    return f"L{m.group(1)}" if m else "L?"


# ─── B 类：从书籍档案抽取 ─────────────────────────────────────────────────────

def _parse_meta_section(profile_md):
    """返回书籍档案 '## 海报/指南元数据' 块的原文，找不到返回 ''。"""
    m = re.search(r"##\s*海报/指南元数据[^\n]*\n(.*?)(?=\n##|\Z)", profile_md, re.S)
    return m.group(1) if m else ""


def _parse_simple_field(section, label):
    """从元数据块取 '- label：value' 的单行值，缺失/占位返回 None。"""
    m = re.search(r"^-\s*" + re.escape(label) + r"[：:](.*)$", section, re.M)
    if m:
        val = m.group(1).strip()
        return None if _is_blank(val) else val
    return None


def parse_author_from_archive(profile_md):
    """
    从书籍档案 '## 一、基本信息' 里抽作者。
    兼容两种写法：
      1. '- 作者：冯骥才'
      2. '- 作者 / 译者 / 出版社 / 页数 / 字数：冯骥才 / 著 / ...'
      3. '- 作者:[美] 盖瑞·伯森'
    """
    # 先找基本信息块
    sec_m = re.search(r"##\s*一[、.]?\s*基本信息(.*?)(?=\n##|\Z)", profile_md, re.S)
    section = sec_m.group(1) if sec_m else profile_md

    # 匹配 "- 作者..." 行（不含 "作者简介"）
    m = re.search(r"^-\s*作者(?!简介)[^：:\n]*[：:](.+)$", section, re.M)
    if not m:
        return None
    raw = m.group(1).strip()
    # 复合写法：取第一个"/"之前的部分
    first = raw.split("/")[0].strip()
    return None if _is_blank(first) else first


def parse_book_meta(profile_md):
    """从书籍档案的 '## 海报/指南元数据' 块抽取等级/作者/出版社/字数/页数。"""
    section = _parse_meta_section(profile_md)
    return {
        "level":      _parse_simple_field(section, "等级"),
        "author":     _parse_simple_field(section, "作者"),
        "publisher":  _parse_simple_field(section, "出版社"),
        "word_count": _parse_simple_field(section, "字数"),
        "page_count": _parse_simple_field(section, "页数"),
    }


# ─── 骨架构建 ─────────────────────────────────────────────────────────────────

def build_skeleton(lesson_md, profile_md=None):
    # A 类：硬门槛检查
    title = extract_title(lesson_md)
    if not title:
        sys.stderr.write(
            "[ERROR] Course plan missing title (# <<BookName>>). Cannot proceed.\n"
        )
        sys.exit(2)

    # B 类：优先书籍档案，缺失留占位
    meta = parse_book_meta(profile_md) if profile_md else {}
    author_from_archive = parse_author_from_archive(profile_md) if profile_md else None

    # 等级：先用课案 L 号，抽不到再回退机读块「- 等级：」
    level = extract_level(lesson_md)
    if level == "L?":
        level = meta.get("level") or "L?"

    def b(key):
        val = meta.get(key)
        return val if val is not None else PLACEHOLDER[key]

    data = {
        # A 类
        "title":      title,
        "level":      level,
        # B 类（作者：先机读块「- 作者：」，回退「基本信息」块，再回退占位）
        "author":     meta.get("author") or author_from_archive or PLACEHOLDER["author"],
        "publisher":  b("publisher"),
        "word_count": b("word_count"),
        "page_count": b("page_count"),
        # C 类（AI 必须填实）
        "summary":    C_SUMMARY_TODO,
    }
    return data


# ─── 入口 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="从课案(.md)和书籍档案(.md)提取书目卡字段，生成骨架 data.json"
    )
    ap.add_argument("md",        help="课案详案 .md 路径")
    ap.add_argument("out_json",  help="输出 data.json 路径")
    ap.add_argument(
        "--profile",
        default=None,
        help="书籍档案 .md 路径（须含 '## 海报/指南元数据' 块和 '## 一、基本信息' 块）",
    )
    args = ap.parse_args()

    lesson_md  = read(args.md)
    profile_md = read(args.profile) if args.profile else None
    data = build_skeleton(lesson_md, profile_md)

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    out = sys.stdout
    if hasattr(out, "reconfigure"):
        out.reconfigure(encoding="utf-8")
    print(f"[OK] JSON: {args.out_json}", file=out)
    print(f"  title: {data['title']}  level: {data['level']}", file=out)
    if profile_md:
        filled = [k for k in ("author", "publisher", "word_count", "page_count")
                  if "请回填" not in str(data.get(k, "请回填"))]
        print(f"  profile filled: {', '.join(filled) if filled else 'none'}", file=out)
    print("  [!] 'summary' is C-class placeholder. AI must fill from lesson plan before rendering.", file=out)
