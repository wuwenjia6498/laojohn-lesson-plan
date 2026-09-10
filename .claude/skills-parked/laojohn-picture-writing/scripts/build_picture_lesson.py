# -*- coding: utf-8 -*-
"""
build_picture_lesson —— 看图写话自动生图闭环「一键串联」：
  生图+验收(generate_images) → docx 回插(insert_images_docx)。
失败隔离：生图失败也仍尝试回插（已生成的图照插、缺的留灰字待补）。

用法：
  export AIHUBMIX_API_KEY=sk-xxx
  PYTHONUTF8=1 python build_picture_lesson.py <详案.md> [--max-retries N] [--width-cm 12] [--skip-gen]

  --skip-gen  跳过生图、只回插（图位目录已有图时用）。
"""
import os
import sys
import argparse
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))


def _run(script, *script_args):
    cmd = [sys.executable, os.path.join(_HERE, script), *script_args]
    print(f'\n$ {script} {" ".join(script_args)}')
    return subprocess.call(cmd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('md_path')
    ap.add_argument('--max-retries', default=None)
    # 默认 None＝不往下传，让图宽由共享回插件的 PROFILES['picture'] 裁决。
    # 若在此写死数值，会静默盖住课型档（调了 profile 也不生效，且无任何报错）。
    ap.add_argument('--width-cm', default=None)
    ap.add_argument('--skip-gen', action='store_true')
    args = ap.parse_args()

    if not args.skip_gen:
        gen_args = [args.md_path]
        if args.max_retries is not None:
            gen_args += ['--max-retries', str(args.max_retries)]
        rc = _run('generate_images.py', *gen_args)
        if rc != 0:
            print('[提醒] 生图阶段非零退出，仍继续回插已生成的图。')

    insert_args = [args.md_path]
    if args.width_cm is not None:
        insert_args += ['--width-cm', str(args.width_cm)]
    rc = _run('insert_images_docx.py', *insert_args)
    sys.exit(rc)


if __name__ == '__main__':
    main()
