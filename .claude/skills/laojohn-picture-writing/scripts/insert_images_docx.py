# -*- coding: utf-8 -*-
"""
insert_images_docx —— 看图写话「回插后处理」。不碰 CLAUDE.md §3 跨技能共享 docx 引擎：
先用共享引擎把详案 .md 出基础 docx（引擎把 `【图位:编号】` 原样印为文字），
再用 python-docx 打开，把每个含 `【图位:编号】` 的段落就地换成 图位/<编号>.png 真图。
缺图则保留标记并追加灰字「（图位 <编号> 待补）」，不抛错。

用法：
  PYTHONUTF8=1 python insert_images_docx.py <详案.md> [--base-docx 已有基础.docx] [--width-cm 12]
输出：<详案名>-配图.docx（不覆盖无图版，便于对照）。
"""
import os
import re
import sys
import tempfile
import argparse
import subprocess

import imgspec_parser as ip

_ENGINE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'laojohn-lesson-plan', 'assets', 'md_to_laojohn_docx.py'))

_PLACE_RE = re.compile(r'【图位[：:]\s*([锚例格]-\d+)[^】]*】')


def _ensure_docx():
    try:
        import docx  # noqa
        return
    except ImportError:
        pass
    for args in (
        [sys.executable, '-m', 'pip', 'install', '-q', 'python-docx'],
        [sys.executable, '-m', 'pip', 'install', '-q', '--user', 'python-docx'],
    ):
        try:
            subprocess.check_call(args)
            import docx  # noqa
            return
        except Exception:
            continue
    print('[错误] 无法自动安装 python-docx，请手动安装后重试。')
    sys.exit(1)


def build_base_docx(md_path):
    """调共享引擎产基础 docx（落临时文件，绝不碰用户已导出的同名 docx）。"""
    fd, base = tempfile.mkstemp(prefix='看图写话基础_', suffix='.docx')
    os.close(fd)
    subprocess.check_call([sys.executable, _ENGINE, md_path, base])
    return base


def _clear_paragraph(p):
    for r in list(p.runs):
        r._element.getparent().remove(r._element)


def insert(md_path, base_docx, width_cm):
    from docx import Document
    from docx.shared import Cm, RGBColor

    doc = Document(base_docx)
    inserted, missing, fmt_skipped = [], [], []
    for p in doc.paragraphs:
        m = _PLACE_RE.search(p.text)
        if not m:
            continue
        code = m.group(1)
        if code.startswith('格-'):           # 格式图：固定资产，不在此自动回插
            fmt_skipped.append(code)
            continue
        png = ip.image_path(md_path, code)
        _clear_paragraph(p)
        if os.path.isfile(png):
            run = p.add_run()
            run.add_picture(png, width=Cm(width_cm))
            try:
                p.alignment = 1  # 居中
            except Exception:
                pass
            inserted.append(code)
        else:
            run = p.add_run(f'【图位 {code} 待补：未找到 {os.path.basename(png)}】')
            try:
                run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
            except Exception:
                pass
            missing.append(code)

    out = os.path.splitext(md_path)[0] + '-配图.docx'
    doc.save(out)
    return out, inserted, missing, fmt_skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('md_path')
    ap.add_argument('--base-docx', default='', help='已有基础 docx；不给则现调引擎生成')
    ap.add_argument('--width-cm', type=float, default=12.0)
    args = ap.parse_args()

    _ensure_docx()
    temp_base = not args.base_docx
    base = args.base_docx or build_base_docx(args.md_path)
    try:
        out, inserted, missing, fmt = insert(args.md_path, base, args.width_cm)
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
