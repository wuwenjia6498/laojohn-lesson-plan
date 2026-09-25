"""gen_cutouts.py - 生成「透明底人物件」，供课件嵌图时立在底带／页边上（2026-09-25 六上五试点加）。

为什么单独一条：页目图带水彩底晕，后期抠图总有残留（用户两轮点名「没抠干净」）；
gpt-image 能直接出透明底 PNG，从源头就没有底。只支持 gpt-image 通道。

项目 JSON 里加一个列表 "抠图件"：
  {"id": "抠-P23", "画幅": "4:3", "prompt": "…只画人物和道具…", "挂载": ["主角色男孩-半身"]}
挂载可写角色件 id 或页码（同 run_lesson.resolve_refs）。画风由 run_lesson.compose 拼（与页目同一套）。
产出：课件产出/<项目>/<通道>/抠图/<id>.png

    python scripts/gen_cutouts.py 课件项目/<项目>.json [--only 抠-P23 抠-P26] [--force]
"""
import argparse
import base64
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import imgclient  # noqa: E402

_spec = importlib.util.spec_from_file_location("run_lesson", HERE / "run_lesson.py")
run_lesson = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_lesson)

TAIL = "；只画人物和必要道具，其余全部透明，不画地面、不画阴影、不画任何底色晕染或背景色块"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    proj = pathlib.Path(a.project)
    d = json.loads(proj.read_text(encoding="utf-8"))
    client = imgclient.make_client("gpt-image")
    outdir = run_lesson.ROOT / "课件产出" / proj.stem / "gpt-image" if hasattr(run_lesson, "ROOT") \
        else HERE.parent / "课件产出" / proj.stem / "gpt-image"
    dst = outdir / "抠图"
    dst.mkdir(parents=True, exist_ok=True)
    for c in d.get("抠图件", []):
        if a.only and c["id"] not in a.only:
            continue
        out = dst / f"{c['id']}.png"
        if out.exists() and not a.force:
            print(f"  [已有] {out.name}")
            continue
        refs = run_lesson.resolve_refs(c.get("挂载"), outdir, {})
        body = c["prompt"].rstrip("。；，") + TAIL
        prompt, refs = run_lesson.compose(d["style_card"], {"prompt": body}, refs)
        try:
            data = client.generate(prompt, ratio=c.get("画幅", "4:3"), images=refs or None,
                                   background="transparent")
        except RuntimeError as e:
            print(f"  [失败] {c['id']}：{e}")
            continue
        out.write_bytes(data)
        print(f"  [生成] {out.name}")
    print("用量：", client.usage)


if __name__ == "__main__":
    main()
