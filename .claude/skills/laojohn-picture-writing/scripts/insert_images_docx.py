# -*- coding: utf-8 -*-
"""
insert_images_docx（看图写话薄 shim）——实现已上移为跨技能共享件：
  .claude/skills/laojohn-lesson-plan/assets/insert_images_docx.py（见 CLAUDE.md §3）
本文件只做一件事：把**看图写话专属**的取图口径（imgspec_parser.image_dir）注入共享件。
页眉、编号前缀集、跳过前缀、图宽等课型差异，收在共享件顶部 PROFILES['picture'] 里。

CLI 与 stdout 摘要与上移前逐字一致，故 build_picture_lesson.py 无需改动。

用法：
  PYTHONUTF8=1 python insert_images_docx.py <详案.md> [--base-docx 已有基础.docx] [--width-cm 12]
输出：<详案名>-配图.docx（不覆盖无图版，便于对照）。
"""
import os
import sys
import argparse
import importlib.util

import imgspec_parser as ip

_SHARED = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'laojohn-lesson-plan', 'assets', 'insert_images_docx.py'))


def _load_shared():
    """按相对路径载共享件（同 book-card/course-poster 载 profile_meta 的成例）。
    改 skill 目录名或挪 scripts 目录会静默断链——报错要说清。"""
    if not os.path.isfile(_SHARED):
        print(f'[错误] 找不到共享回插件：{_SHARED}\n'
              f'  （CLAUDE.md §3：本文件是薄 shim，实现在 laojohn-lesson-plan/assets/）')
        sys.exit(1)
    spec = importlib.util.spec_from_file_location('_shared_insert_images', _SHARED)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('md_path')
    ap.add_argument('--base-docx', default='', help='已有基础 docx；不给则现调引擎生成')
    # None＝跟随共享件 PROFILES['picture']['width_cm']（勿给硬默认，见共享件注释）
    ap.add_argument('--width-cm', type=float, default=None)
    args = ap.parse_args()

    sh = _load_shared()
    prof = sh.PROFILES['picture']
    # 前缀集以 imgspec_parser 为单一源（占位正则与取图口径都归它），共享件的
    # profile 值只作 fallback；两者不一致时以此处为准并提醒。
    prefixes = getattr(ip, 'CODE_PREFIXES', prof['code_prefixes'])
    if prefixes != prof['code_prefixes']:
        print(f'[提醒] 编号前缀集不一致：imgspec_parser={prefixes!r} '
              f'≠ 共享件 PROFILES[picture]={prof["code_prefixes"]!r}，本次以前者为准。')
    place_re = sh.make_place_re(prefixes)
    width = args.width_cm if args.width_cm is not None else prof['width_cm']

    sh._ensure_docx()
    temp_base = not args.base_docx
    base = args.base_docx or sh.build_base_docx(
        args.md_path, prof['header_left'], prof['header_right'])
    try:
        out, inserted, missing, fmt = sh.insert(
            args.md_path, base, place_re=place_re,
            images_dir=ip.image_dir(args.md_path),
            width_cm=width, max_height_cm=prof['max_height_cm'],
            skip_prefixes=prof['skip_prefixes'], caption=prof['caption'],
            img_exts=prof['img_exts'])
    finally:
        if temp_base and os.path.exists(base):
            try:
                os.remove(base)
            except OSError:
                pass
    print(f'回插完成：{out}')
    print(f'  插入 {len(inserted)} 张：{inserted}')
    if missing:
        print(f'  缺图待补 {len(missing)}：{missing}（已在文中留灰字提示）')
    if fmt:
        print(f'  跳过格式图 {len(set(fmt))}：{sorted(set(fmt))}（固定资产，手动插）')


if __name__ == '__main__':
    main()
