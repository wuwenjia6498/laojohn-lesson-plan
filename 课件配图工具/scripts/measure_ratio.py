# -*- coding: utf-8 -*-
"""头身比像素量测（T1 的客观判据，不依赖视觉模型估数）。

适用前提：单人、全身入镜、纯浅色背景的定妆图。
做法：按亮度阈值切出人物前景 → 取头顶行与脚底行；再在上部扫描每行前景宽度，
     取「第一个局部极大之后的第一个局部极小」为颈线 → 头身比 = 全身高 / 头高。
     颈线略低于真实下巴，故读数比学院派头身比略偏小；本工具只用于同条件下的横向对比。
颈部极小值找不到（如半身像、复杂背景）时返回 None，交人工目测，不硬给数。

用法：python scripts/measure_ratio.py <图片...>
"""
import sys
import pathlib

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")


def measure(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(int)
    h, w = a.shape[:2]
    # 前景 = 与背景差异大的像素。背景色取「最左最右两条竖边」的中位色，不取四角。
    # ⚠ 别改回四角：Gemini 爱在人物背后刷一大片水彩晕染，晕染常常正好盖住上方两角，
    #   于是「四角中位色」取成了晕染色，人物反倒被判成背景，量测直接失败（实测 1a-1）。
    #   竖边取样避开了这种居中的装饰色块；豆包背景干净，两种取法结果一致。
    edge = np.concatenate([a[:, :24].reshape(-1, 3), a[:, -24:].reshape(-1, 3)])
    bg = np.median(edge, axis=0)
    diff = np.abs(a - bg).sum(axis=2)
    fg = diff > 45
    # 背景纯度自检。装饰性晕染的色差不大不小（比人物淡、比纯背景深），会大面积落在中间带，
    # 把行宽曲线整个带偏、颈线判进头发里。**这时该报「前提不成立」，不是硬算一个数**——
    # prompt 本来就写着「纯浅色背景」，背景不纯说明这张图没照规格画，量测该拒绝作答。
    wash = float(((diff > 18) & (diff <= 60)).mean())
    # 阈值 0.30 是照实测断层定的：肉眼确认有大片晕染的那张是 47%，其余（含水彩纸纹）
    # 都 ≤18%，中间是空的。切在 12% 会把只有纸纹的干净图一起误杀——
    # 判据切在没有断层的地方，等于按噪声下结论。换画风/换通道后须重新看这个分布。
    if wash > 0.30:
        return {"图": pathlib.Path(path).name, "头身比": None,
                "备注": "背景不纯（%.0f%% 的像素是中等色差，多半是装饰性晕染/底色块），"
                        "与「纯浅色背景」的规格不符；本工具的前景切分前提不成立，"
                        "请改用干净背景重出，或人工目测" % (wash * 100)}
    # 去噪：每行前景像素数需超过画面宽度的 1%
    rows = fg.sum(axis=1)
    valid = np.where(rows > w * 0.01)[0]
    if valid.size == 0:
        return None
    top, bottom = int(valid[0]), int(valid[-1])
    body = bottom - top
    # 找颈线：颈部一定比它上面的头和它下面的肩都窄，所以在「身高 8%~33%」这条带里
    # 取全局最窄行即可（该带对 3~7 头身都覆盖得住）。
    # ⚠ 两种更朴素的写法都踩过坑，别改回去：取上部最宽行会选中毛衣/肩（比头还宽），
    #   取「第一个局部极大后的第一个极小」会被顶端发梢的细碎噪声打断。
    k = max(int(body * 0.02), 7)
    sm = np.convolve(rows.astype(float), np.ones(k) / k, mode="same")
    lo, hi = top + int(body * 0.08), top + int(body * 0.33)
    if hi - lo < 10:
        return {"图": pathlib.Path(path).name, "头身比": None, "备注": "人物过小，无法量测"}
    chin = lo + int(np.argmin(sm[lo:hi]))
    head = chin - top
    if head <= 0 or not (0.08 <= head / body <= 0.40):
        return {"图": pathlib.Path(path).name, "头身比": None,
                "备注": "颈部识别不可信（可能是半身像、多人或背景不纯），请人工目测"}
    return {"图": pathlib.Path(path).name, "头顶y": top, "颈线y": chin, "脚底y": bottom,
            "头高px": head, "全身高px": body, "头身比": round(body / head, 2),
            "前提": "假设人物前景的最下缘＝脚底。若人物被画框截断（非全身入镜），"
                    "本读数不成立——像素判不出「这是脚还是被截断的大腿」，须由人或视觉模型先确认"}


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(measure(p))
