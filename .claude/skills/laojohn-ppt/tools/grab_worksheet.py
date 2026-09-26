"""grab_worksheet.py - 从写作配套「学生用.html」现截稿纸页上部，给课件 PPT 的稿纸页用（2026-09-26 立）。

为什么有它：外部人工终稿在「自由写作」说明页后都插一页稿纸页，图是学生用第 2 页的静态截图，
配套一改就过期（记忆 materials-template-optional-fields-0922）。仓内直出每次出件都用本脚本重截，
截图永远跟着当前配套走。

截的是 `.sheet.page2`（写作稿纸页）从页题「写作稿纸」起的上部：页题、写法提示、前几行格子（跳过页眉 logo）。
宽高比缺省 1.86，与三套终稿的图位（约 14.6×7.87 英寸）一致；2.5 倍像素密度，投屏够清楚。

    python grab_worksheet.py 写作配套输出/<课次>/<课次>-学生用.html 输出.png [--ratio 1.86]
"""
import argparse
import os
import pathlib

os.environ.setdefault(
    "PLAYWRIGHT_BROWSERS_PATH",
    os.path.join(os.path.expanduser("~"), "AppData", "Local", "ms-playwright"),
)


def grab(html, out, ratio=1.86, scale=2.5, selector=".sheet.page2"):
    from playwright.sync_api import sync_playwright

    html = pathlib.Path(html).resolve()
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        page = br.new_page(viewport={"width": 1200, "height": 1600}, device_scale_factor=scale)
        page.goto(html.as_uri())
        page.wait_for_load_state("networkidle")
        page.evaluate("document.fonts.ready")
        el = page.query_selector(selector)
        if el is None:
            br.close()
            raise SystemExit(f"找不到 {selector}：这份学生用 html 没有稿纸页？")
        box = el.bounding_box()
        # 从页题「写作稿纸」起截，跳过页眉 logo 与上边距（与三套终稿的截法一致）
        top = page.evaluate("""(el) => {
            let best = null;
            for (const e of el.querySelectorAll('*')) {
                if (e.children.length > 3) continue;
                if ((e.textContent || '').trim().startsWith('写作稿纸')) {
                    const r = e.getBoundingClientRect();
                    if (!best || r.height < best.height) best = r;
                }
            }
            return best ? best.top + window.scrollY - 14 : null;
        }""", el)
        y0 = box["y"] if top is None else max(box["y"], top)
        h = min(box["y"] + box["height"] - y0, box["width"] / ratio)
        page.screenshot(path=str(out), clip={"x": box["x"], "y": y0, "width": box["width"], "height": h},
                        full_page=True)
        br.close()
    print(f"已截稿纸页 → {out}（{box['width']:.0f}×{h:.0f}px ×{scale}）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("out")
    ap.add_argument("--ratio", type=float, default=1.86)
    a = ap.parse_args()
    grab(a.html, a.out, a.ratio)


if __name__ == "__main__":
    main()
