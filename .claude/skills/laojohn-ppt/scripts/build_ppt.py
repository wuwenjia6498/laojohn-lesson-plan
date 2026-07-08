# -*- coding: utf-8 -*-
"""build_ppt.py - 把中间稿 .md 编译为 .pptx

用法：
    python build_ppt.py --input 中间稿.md --output 课件.pptx [--course 导读课] [--book 俗世奇人]
    python build_ppt.py --input 中间稿.md --output 课件.pptx --logo path/to/logo.png --banner path/to/banner.jpg

如果 --logo / --banner 未指定，会自动从 ../assets/logo/ 和 ../assets/decorations/ 取默认资源。
"""
import argparse
import os

from pptx import Presentation

import theme
from parser import parse_md, Page
from layouts_reading import RENDERERS_READING
from layouts_writing import RENDERERS_WRITING


def find_default_asset(filename_candidates, asset_subdir):
    here = os.path.dirname(os.path.abspath(__file__))
    base = os.path.normpath(os.path.join(here, "..", "assets", asset_subdir))
    if not os.path.isdir(base):
        return None
    for name in filename_candidates:
        p = os.path.join(base, name)
        if os.path.isfile(p):
            return p
    # 兜底：返回该目录第一个 png/jpg
    for fn in sorted(os.listdir(base)):
        if fn.lower().endswith((".png", ".jpg", ".jpeg")):
            return os.path.join(base, fn)
    return None


def build(input_md: str, output_pptx: str, *,
          course_name: str = "", book_title: str = "",
          logo_path: str = None, banner_path: str = None,
          anim: bool = True) -> dict:
    with open(input_md, encoding="utf-8") as f:
        md = f.read()

    deck = parse_md(md)
    # 命令行参数覆盖元信息
    if course_name:
        deck.course = course_name
    if book_title:
        deck.title = book_title

    # 按文体选 profile：写作课 → 写作 renderer 集；否则读书会（缺省/向后兼容）
    renderers = RENDERERS_WRITING if deck.doc_kind == "写作" else RENDERERS_READING

    # 默认资源
    if logo_path is None:
        logo_path = find_default_asset(["logo-red.png", "logo.png"], "logo")
    if banner_path is None:
        banner_path = find_default_asset(["cover-banner.jpg", "banner.jpg", "banner.png"], "decorations")
    # END 页用白色 LOGO（找不到时回退红色）
    logo_white_path = find_default_asset(["logo-white.png"], "logo") or logo_path

    prs = Presentation()
    prs.slide_width = theme.SLIDE_W
    prs.slide_height = theme.SLIDE_H
    blank_layout = prs.slide_layouts[6]

    # ===== 自动注入封面 + END =====
    # 中间稿 P 编号由 ppt-draft 工具自排（每课时 P01=封面、正文从 P02 起），仅作内部引用；PPT 不标注页码。
    pages = list(deck.pages)

    # 1) 若首页不是封面，按"和导读课起始页一样"的规则注入一页封面
    if not pages or pages[0].page_type != "封面":
        synthetic_cover = Page(num=0, page_type="封面")
        # 标题留空：render_cover 会回退到 ctx["book_title"]
        # 副标题留空：会回退到 ctx["course_name"]
        # body 留空：会回退到 ctx["meta"]（作者 · 年级）
        pages.insert(0, synthetic_cover)

    # 2) 始终追加一页 END
    pages.append(Page(num=999, page_type="_END"))

    # 3) 给每个"环节标题"页打章节序号（课时内从 1 递增）
    section_counter = 0
    for p in pages:
        if p.page_type == "环节标题":
            section_counter += 1
            p._section_no = section_counter
    section_total = sum(1 for p in pages if p.page_type == "环节标题")
    for p in pages:
        if p.page_type == "环节标题":
            p._section_total = section_total

    # 页码：仅对中间内容页计数（封面、END 不纳入）
    inner_total = sum(1 for p in pages if p.page_type not in {"封面", "_END"})
    placeholder_report = []
    inner_idx = 0

    for page in pages:
        slide = prs.slides.add_slide(blank_layout)
        is_inner = page.page_type not in {"封面", "_END"}
        if is_inner:
            inner_idx += 1

        ctx = {
            "course_name": deck.course or course_name,
            "book_title": deck.title or book_title,
            "page_index": inner_idx,
            "page_total": inner_total,
            "logo_path": logo_path,
            "logo_white_path": logo_white_path,
            "banner_path": banner_path,
            "meta": "　·　".join(p for p in (deck.author, deck.grade) if p),
            "doc_kind": deck.doc_kind,
            "anim": anim,
        }
        renderer = renderers.get(page.page_type)
        if renderer is None:
            raise ValueError(f"P{page.num} 无渲染器：{page.page_type}")
        renderer(slide, page, ctx)

        # 占位清单（仅对中间稿原生页报告，跳过 synthetic）
        if page.page_type in {"_END", "封面"} and page.num in {0, 999}:
            continue
        if page.page_type == "填空表格" and page.table_reveals:
            placeholder_report.append(
                (page.num, page.page_type,
                 f"[填空表格] {len(page.table_reveals)} 格答案逐格点击"))
            continue
        raw_sugs = page.image_suggestions or ([page.image_suggestion] if page.image_suggestion else [])
        sugs = [s.strip() for s in raw_sugs
                if s and s.strip() not in {"无", "无（页面已满）", "—", "无配图"}]
        if sugs and page.page_type in {"引导问题", "要点小结", "环节标题"}:
            if len(sugs) >= 2:
                placeholder_report.append(
                    (page.num, page.page_type, f"[四图网格×{len(sugs)}] " + " ／ ".join(sugs)))
            else:
                placeholder_report.append((page.num, page.page_type, sugs[0]))
        else:
            placeholder_report.append((page.num, page.page_type, "—"))

    total = len(pages)

    os.makedirs(os.path.dirname(os.path.abspath(output_pptx)) or ".", exist_ok=True)
    prs.save(output_pptx)

    return {
        "pages": total,
        "output": os.path.abspath(output_pptx),
        "placeholders": placeholder_report,
        "logo": logo_path,
        "banner": banner_path,
    }


def main():
    ap = argparse.ArgumentParser(description="老约翰投屏 PPT 编译器")
    ap.add_argument("--input", "-i", required=True, help="中间稿 .md 路径")
    ap.add_argument("--output", "-o", required=True, help="输出 .pptx 路径")
    ap.add_argument("--course", default="", help="课时名（覆盖中间稿元信息）")
    ap.add_argument("--book", default="", help="书名（覆盖中间稿元信息）")
    ap.add_argument("--logo", default=None, help="LOGO 图片路径")
    ap.add_argument("--banner", default=None, help="封面横幅图片路径")
    ap.add_argument("--no-anim", dest="anim", action="store_false",
                    help="关闭逐条点击动画（默认开启：要点小结/引导问题追问逐条淡入）")
    args = ap.parse_args()

    info = build(
        args.input, args.output,
        course_name=args.course,
        book_title=args.book,
        logo_path=args.logo,
        banner_path=args.banner,
        anim=args.anim,
    )

    print(f"[OK] 已生成 {info['pages']} 页 -> {info['output']}")
    print(f"     LOGO: {info['logo']}")
    print(f"     横幅: {info['banner']}")
    print()
    print("配图占位清单：")
    for num, ptype, sug in info["placeholders"]:
        print(f"  P{num:02d}  [{ptype}]  {sug}")


if __name__ == "__main__":
    main()
