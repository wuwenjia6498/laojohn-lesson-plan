---
name: worksheet-blank-box-fix-1019
description: 旧版读书会阅读单（D:\00000读书会课案 二～六年级）空导图框补提示/重画已全部完成；工具、规则、产出位置
metadata:
  node_type: memory
  type: project
  originSessionId: e209b1c4-c5bc-488f-b806-9abac5bdc2fe
  modified: 2026-10-19T11:02:25.123Z
---

2026-10-19 起源于加盟老师反馈「阅读单一排空框没写填什么」。普查二(优化版43本)～六年级，清单 `D:\00000读书会课案\阅读单同类问题清单（二至六年级）.xlsx`：严重22/中33/轻22 共77页全部「已修（10/19）」，边界5页用户定不改；一年级、二年级旧版40本未查。

- 产出：各书 `阅读单优化后文件\`，与原件**同名**（用户定去掉「-优化」），原件不动；学生用资料同步改并导PDF（只有PDF的按文字相似度换页）。
- 工具（持久目录，scratchpad会被360清理Pro定期清空别放，见[[temp-cleaner-wipes-scratchpad-1019]]）：`C:\Users\69491\AppData\Local\laojohn-wsfix\`——wsfix.py（叠提示/重画/COM导出）、BRIEF.md（子agent通用规则）、snapshot/finalize/validate_all/mark_excel.py、work\ 各组脚本、anim_scan.py。
- 口径：提示词只写「填什么类型」须有出处（答案页/详案）；重画只改版式不改图型；用户授权顺手改原课件错误（图片里的错字用遮盖叠字）；未改：我家没有英雄第3/4章、星期天的巨人12/13个、斑比「鹿王/鹿王子」——均需对原书核实。
- 坑：python-pptx 代理对象不能用 `is` 比对（Canvas keep 曾失效）；删形状要清动画引用；在单击出现的图片上加标签须挂「与上一动画同时」；PowerPoint COM 偶发 Open 失败重试即可；部分 WPS 存的原件 PowerPoint 打不开。
