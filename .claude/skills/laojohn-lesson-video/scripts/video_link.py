# -*- coding: utf-8 -*-
r"""备课视频链的「四源绑定」：按课次标识定位详案/PPT/教师用 json/动画工作单 + md5 记账。
单一源，供链上各脚本 import。

**为什么不搜索、只拼路径**：同 laojohn-ppt 的 plan_link.py——题目里带弯引号（`小小“动物园”`）
或全角下划线（`我和＿＿过一天`）的课次，用通配去搜一个都搜不到，会误判成「文件不存在」而
静默跳过整道工序。课次标识段是全线统一口径（CLAUDE.md §7），拼路径不受这些字符影响。

    from video_link import Sources
    src = Sources.of("三上-第一单元-猜猜他是谁")   # 缺件会抛 SourceMissing，消息里带候选清单
    src.plan_md                                    # 详案 md 路径（页码权威源）
    src.digest()                                   # 四源 md5，写进分镜单 meta，供下游闸门校验
"""
import hashlib
import json
import os

PLAN_DIR = "写作课详案输出"
PLAN_SUFFIX = "-写作课详案.md"
PPT_DIR = "写作课件PPT输出"
DRAFT_DIR = "写作课件中间稿输出"
KIT_DIR = "写作配套输出"
WORK_DIR = "_备课视频工作区"
OUT_DIR = "写作课备课视频输出"


class SourceMissing(Exception):
    pass


def project_root(start=None):
    r"""从当前目录往上找，直到看见 写作课详案输出\ —— 禁硬编码盘符（移动硬盘，CLAUDE.md §1）。"""
    p = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.isdir(os.path.join(p, PLAN_DIR)):
            return p
        up = os.path.dirname(p)
        if up == p:
            raise SourceMissing(r"往上找不到 %s\ —— 确认在项目目录内运行" % PLAN_DIR)
        p = up


def units(root):
    """⚠ 排除 `_` 开头的文件：`_润色报告-<课次>-写作课详案.md` 也以 PLAN_SUFFIX 结尾，
    不滤掉的话课次清单里会混进一堆假课次（实测混进 9 个润色报告）。"""
    d = os.path.join(root, PLAN_DIR)
    return sorted(fn[: -len(PLAN_SUFFIX)] for fn in os.listdir(d)
                  if fn.endswith(PLAN_SUFFIX) and not fn.startswith("_"))


def md5(path):
    if not path or not os.path.exists(path):
        return None
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Sources(object):
    def __init__(self, root, unit):
        self.root = root
        self.unit = unit
        j = lambda *a: os.path.join(root, *a)
        self.plan_md = j(PLAN_DIR, unit + PLAN_SUFFIX)
        self.repo_pptx = self._one(j(PPT_DIR, unit), "-课件PPT.pptx")
        self.anim_json = self._one(j(PPT_DIR, unit), "-课件PPT-anim.json")
        self.pagemap = self._one(j(DRAFT_DIR, unit), "-页标映射.json")
        self.teacher_json = j(KIT_DIR, unit, unit + "-教师用_data.json")
        self.final_pptx = j(WORK_DIR, unit, "source.pptx")
        self.out_dir = j(OUT_DIR, unit)

    @staticmethod
    def _one(d, suffix):
        """目录里唯一一个以 suffix 结尾的文件；没有就返回 None（由调用方决定是否致命）。"""
        if not os.path.isdir(d):
            return None
        hits = sorted(fn for fn in os.listdir(d) if fn.endswith(suffix))
        return os.path.join(d, hits[0]) if hits else None

    @classmethod
    def of(cls, unit, root=None):
        root = root or project_root()
        all_units = units(root)
        if unit not in all_units:
            raise SourceMissing(
                "没有课次「%s」的详案。现有 %d 个：\n  %s"
                % (unit, len(all_units), "\n  ".join(all_units)))
        s = cls(root, unit)
        lack = [n for n, p in (("详案 md", s.plan_md),
                               ("仓内 pptx", s.repo_pptx),
                               ("教师用 json", s.teacher_json))
                if not p or not os.path.exists(p)]
        if lack:
            raise SourceMissing(
                "课次「%s」缺件：%s\n"
                "  —— PPT 链未跑完的课次做不了备课视频（画面无源），先走 laojohn-ppt 的后处理链。"
                % (unit, "、".join(lack)))
        return s

    def visual_pptx(self, fallback=False):
        """画面源。默认用外部终稿；取不到时**明确报错**，不静默回退——
        静默回退会产出一批页码可能对不上的片子，而失配没有任何报错。"""
        if os.path.exists(self.final_pptx):
            return self.final_pptx, "final"
        if fallback:
            return self.repo_pptx, "repo"
        raise SourceMissing(
            "找不到外部终稿：%s\n"
            "  把老师实际在用的那份 pptx 拷进去（不进 git，工作区整目录已 ignore）。\n"
            "  确要用仓内 anim 版出图，加 --fallback-repo-pptx（画面是 256 色量化版，\n"
            "  且外部人工后补的教材插图不在里面）。" % self.final_pptx)

    def digest(self):
        return {"unit": self.unit,
                "plan_md5": md5(self.plan_md),
                "repo_pptx_md5": md5(self.repo_pptx),
                "final_pptx_md5": md5(self.final_pptx),
                "teacher_json_md5": md5(self.teacher_json),
                "pagemap_md5": md5(self.pagemap)}

    def load_json(self, which):
        p = getattr(self, which)
        if not p or not os.path.exists(p):
            return None
        with open(p, encoding="utf-8") as f:
            return json.load(f)


if __name__ == "__main__":
    import sys
    root = project_root()
    if len(sys.argv) < 2:
        print("课次清单（%d）：" % len(units(root)))
        for u in units(root):
            print("  " + u)
        raise SystemExit(0)
    try:
        s = Sources.of(sys.argv[1], root)
    except SourceMissing as e:
        print(e)
        raise SystemExit(1)
    for k, v in s.digest().items():
        print("%-18s %s" % (k, v))
    for name in ("plan_md", "repo_pptx", "anim_json", "pagemap", "teacher_json", "final_pptx"):
        p = getattr(s, name)
        print("%-14s %s %s" % (name, "OK " if p and os.path.exists(p) else "-- ", p))
