# -*- coding: utf-8 -*-
r"""外部 PPT 后处理链的「详案绑定」：定位详案 + 抽结构摘要。单一源，供链上各脚本 import。

**为什么不搜索、只拼路径**：归位后 pptx 必在 `写作课件PPT输出\<课次>\`，父目录名就是
课次标识，详案就是 `写作课详案输出\<课次>-写作课详案.md`（命名口径见 CLAUDE.md §7）。
2026-08-06 踩过一次：拿 `-Filter "*小小动物园*"` 去搜实际叫 `小小“动物园”` 的课次——
题目带弯引号，一个都搜不到，误判成「详案不存在」，整道审查被跳过，26 页里 8 页分组
按版面猜错顺序、全部返工。按目录名拼路径不受弯引号/全角字符影响，从根上消灭这类失误。

    from plan_link import locate, digest
    md = locate(pptx_path)          # 找不到会抛 PlanNotFound，消息里带候选课次清单
    d = digest(md)                  # {md5, lessons[…], screens[…]}
"""
import hashlib
import io
import os
import re

PLAN_DIR = "写作课详案输出"
PPT_DIR = "写作课件PPT输出"
PLAN_SUFFIX = "-写作课详案.md"

# 「（约 7 分钟）」——课时/环节/方括号子环节的标称时长都用这一种写法
MINUTES = re.compile(r"（约\s*(\d+)\s*[-–~至]?\s*(\d+)?\s*分钟")
# 「### 一、创设情境，明确任务（约 7 分钟）」
STEP_H = re.compile(r"^###\s+(.+?)\s*$")
# 「## 第1课时 · 写作指导课」；附录 `## 附：习作讲评…` 也开新块，但 is_lesson=False——
# 否则附录里的 ### 会挂到最后一个课时名下，把「环节加总＝45 分钟」这道核对搅乱。
SECTION_H = re.compile(r"^##\s+(?!#)(.+?)\s*$")
IS_LESSON = re.compile(r"^第.课时")
# 方括号教师提示块；带时长的那些＝子环节（`[小组轮读（约 6 分钟）：…]`）
BRACKET = re.compile(r"^\[(.+?)[：:\]]")
# 需要屏幕承载的教师指令
SCREEN = re.compile(r"^\[(投屏|发放|出示)")


class PlanNotFound(Exception):
    pass


def project_root(pptx_path):
    """从 pptx 路径回推项目根：<root>/写作课件PPT输出/<课次>/x.pptx。"""
    p = os.path.abspath(pptx_path)
    for up in (os.path.dirname(os.path.dirname(os.path.dirname(p))),
               os.path.dirname(os.path.dirname(p))):
        if os.path.isdir(os.path.join(up, PLAN_DIR)):
            return up
    raise PlanNotFound("从 %s 回推不到项目根（往上找不到 %s\\）——确认 pptx 已归位到"
                       "%s\\<课次>\\ 下（后处理链第 1 步 place_pptx.py）" % (p, PLAN_DIR, PPT_DIR))


def unit_of(pptx_path):
    """课次标识＝pptx 所在的父目录名。"""
    return os.path.basename(os.path.dirname(os.path.abspath(pptx_path)))


def candidates(root):
    d = os.path.join(root, PLAN_DIR)
    return sorted(fn[: -len(PLAN_SUFFIX)] for fn in os.listdir(d) if fn.endswith(PLAN_SUFFIX))


def locate(pptx_path):
    """→ 详案绝对路径。找不到抛 PlanNotFound，消息里列出全部候选课次。"""
    root = project_root(pptx_path)
    unit = unit_of(pptx_path)
    md = os.path.join(root, PLAN_DIR, unit + PLAN_SUFFIX)
    if os.path.isfile(md):
        return md
    lines = ["按 pptx 所在课次目录 %r 拼不出详案：" % unit,
             "  期望 %s" % os.path.relpath(md, root),
             "  %s\\ 下现有课次：" % PLAN_DIR]
    lines += ["    - %s" % u for u in candidates(root)]
    lines.append("  pptx 没归位、或课次目录名与详案文件名不一致（命名口径见 CLAUDE.md §7）。")
    lines.append("  该课确实没有详案时，加 --no-lesson-plan 显式放行。")
    raise PlanNotFound("\n".join(lines))


def _minutes(text):
    m = MINUTES.search(text)
    if not m:
        return None
    return int(m.group(2) or m.group(1))       # 「17–18 分钟」取上界


def digest(md_path):
    """详案结构摘要：课时 → 环节 → 方括号子环节，另收需要屏幕承载的指令。"""
    src = io.open(md_path, encoding="utf-8").read()
    lessons, screens = [], []
    cur_lesson = cur_step = None

    for no, line in enumerate(src.split("\n"), 1):
        m = SECTION_H.match(line)
        if m:
            title = m.group(1).strip()
            cur_lesson = {"title": title, "line": no, "steps": [],
                          "is_lesson": bool(IS_LESSON.match(title))}
            lessons.append(cur_lesson)
            cur_step = None
            continue
        m = STEP_H.match(line)
        if m and cur_lesson is not None:
            cur_step = {"title": m.group(1).strip(), "line": no,
                        "minutes": _minutes(m.group(1)), "subs": []}
            cur_lesson["steps"].append(cur_step)
            continue
        if line.startswith("["):
            if SCREEN.match(line):
                screens.append({"line": no, "text": line.strip()})
            m = BRACKET.match(line)
            if m and cur_step is not None and _minutes(m.group(1)) is not None:
                cur_step["subs"].append({"line": no, "label": m.group(1).strip(),
                                         "minutes": _minutes(m.group(1))})

    return {"md5": hashlib.md5(src.encode("utf-8")).hexdigest(),
            "lessons": lessons, "screens": screens}


def rel(root, path):
    return os.path.relpath(os.path.abspath(path), root).replace("\\", "/")
