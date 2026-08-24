---
name: writing-correction-tool-vercel-deploy-0824
description: 作文批改工具 0824 部署到 Vercel（项目 laojohn-grader，已跑通真实批改）：入口必须是部署根 index.py 且绝不能放 api/、Serverless 下内存限额失效改靠访问口令、国内直连 vercel.app 完全不通
metadata:
  type: project
---

2026-08-24 部署上线（小范围给加盟商试用）。**线上已验真实批改跑通：22 秒返回，
学生名／档位／三条判据／亮点／引用句齐全。**

- Vercel 项目：`wuwenjia6498s-projects/laojohn-grader`
- **正式地址 `https://grader.skyline666.top`**（Cloudflare 解析，证书已签发）
- 访问口令 `laojohn2026`

## DNS 记录值：别信 CLI，以网页端为准

`skyline666.top` 在 Cloudflare，域名下已有二十多条 Vercel 子域名、**全部灰云**。

⚠ **CLI `vercel domains inspect` 给的是 `A 76.76.21.21` 并标 `[recommended]`，
但那是旧文案。**Vercel **项目页 Domains → `View DNS configuration`** 给的才是现行推荐：
**项目专属 CNAME**（本项目＝`cac041b57669b9da.vercel-dns-017.com`），Proxy Disabled。
网页端原话：「We're expanding our IP range」，`76.76.21.21` 与 `cname.vercel-dns.com`
**属 legacy、仍会继续工作**——所以配成 A 也能正常访问，但项目页会一直挂黄色
`DNS Change Recommended`，且 Vercel 扩 IP 段时要手动跟进。0824 就是先配 A、
访问正常、再按网页端换成 CNAME 的（换完全链路复验通过）。

## 入口的位置是硬约束，放错会静默错到很难查

Vercel 的 Python 预设认「**部署根下的 `index.py` 里的顶层 `app`**」，认出来之后
把所有请求都路由给它（API 与前端静态都走这一个函数，与本机行为一致）。
所以**不需要 `rewrites`**，`vercel.json` 里只配 `functions."index.py".maxDuration`。

⚠ **入口绝不能放进 `api/` 目录**——那个目录名在 Vercel 上是另一套语义：
「一个文件一个端点」的旧式文件路由。0824 第一次部署就是这么配的（`api/index.py`
＋ `rewrites` 把 `/api/(.*)` 指过去），结果**所有 `/api/*` 的路径都塌缩成
`/api/index`**，FastAPI 一个路由都匹配不上。**症状会指向完全错误的方向**：
首页 200 正常、`/api/health` 却 401（中间件看到的路径不是 `/api/health`），
带对口令的 `/api/lessons` 返回 `{"detail":"Not Found"}`——看着像口令逻辑写错了，
其实是路由。打包目录同理避开这个名字，叫 `_bundle/`。

## 部署必须两步，漏第一步不报错

```bash
cd 作文批改工具/web
PYTHONUTF8=1 python build_deploy.py    # ← 漏了不报错，线上继续用上次打包的判据
vercel --prod
```

打包这一步存在的理由：线上部署根是 `web/`，够不到上一级的 `../标准包/` 与
`../build_prompt.py`；且标准包文件名带中文与全角引号（`小小“动物园”.json`、
`我和＿＿过一天.json`），要经 git → 构建机 → Lambda zip 三道手，任一道对非 ASCII
文件名处理不一致就**静默少一课**。故合并成单个 `_bundle/_packs.json`。

## Serverless 改变了两条既有结论

1. **内存限额（`_rate_ok`）形同虚设**：每个请求可能落到不同函数实例，每实例一个桶、
   冷启动即清零，累计不起来。原「必须单进程跑」那条在 Vercel 上不成立。
   防盗刷改靠**访问口令** `LJ_ACCESS_CODE`（中间件挡住除 `/api/health` 外全部
   `/api/*`，课次列表也挡——判据是护城河）。要精确限额得上 Redis/KV，是另一轮开发。
2. **`max_image_mb` 已从 8 调到 4**：Vercel 请求体硬限 4.5MB，超了在平台层就挡下，
   函数根本不会被调起，我们自己那句「请在手机上压一压」永远轮不到显示。

## 其它不可推断的事实

- **`.vercelignore` 必须挡掉 `server/config.json`**——vercel CLI **不看 `.gitignore`**，
  那行删了真密钥就进部署包。
- 三个环境变量缺一不可：`AIHUBMIX_API_KEY` / `LJ_ENV=prod` / `LJ_ACCESS_CODE`。
  漏 `LJ_ENV` 最危险（无密钥时静默发假批语，前端毫无异样）。
- Hobby 函数 `maxDuration` **300s 默认即最大**，实测批改 22–61s，够用。
- **国内直连 `*.vercel.app` 完全不通**（本机 curl 全 000，挂系统代理才通）。
  由此：ICP 备案不再是关键路径（境外服务器不需要），但**国内可达性成了新的头号风险**——
  加盟商反馈「转圈/打不开」时先怀疑这里。挂自定义域名 + Cloudflare 能否改善**尚未验证**。
- **本机已装 node v22.14.0 / npm 10.9.2 / Vercel CLI 56.5.0**，且系统代理在
  `127.0.0.1:26001`。⚠ 这推翻了 CLAUDE.md §5 记的「本机无 node/npm」，**0824 已订正该节**
  （复核时另查出第二处过时：openpyxl/pandas 也早装上了，官方 xlsx skill 其实整体可用）。
  订正的重点不是补事实，而是**禁令的风险性质变了**：以前有环境天然挡着、想违反也违反不了，
  现在 node 装上了、违反随时能成功，挡住它的只剩纪律——禁令的理由从来是「绕过品牌版式与闸门」，
  与装没装 node 无关。

相关：[[writing-correction-tool-0818]]

## 标准包核对清单已补齐 14/14（0824）

《猜猜他是谁》《写日记》是最早抽的两个包（0818），当时清单体例还没立（0821 才立），
一直缺凭据。0824 补齐，现在 **14 个标准包 ↔ 14 份清单一一对应**。
⚠ **补清单 ≠ 已核**：`verified_by_human` 仍是 14 个全 false。

**补的过程当场查出一处错**：《写日记》`plan_card_rows` 被错误留空，`notes` 写着
「本课无构思表（特点卡）类工具」，而详案 L117 起是完整一节「日记构思表」环节
（两页 PPT、五行表），配套 `data.json` 的 `worksheet.plan_rows` 也有这五行。
**根因＝把「特点卡」当成构思表的唯一形态**，看到叫「日记构思表」就判成没有。已修
（五行由配套 json 程序化对拍生成，不手打——第一行含全角空格）。

三条可复用的教训：

1. **`validate_packs.py` 全绿证明不了包是对的。** `plan_card_rows` 属
   `OPTIONAL_LIST_FIELDS`，留空不报错，这处错从 0818 藏到 0824。**脚本管格式、
   清单管判断**——这正是 `verified_by_human` 不能靠脚本自动置 true 的原因。
2. **改标准包 JSON 会撞 `D20`：JSON 里禁用直角引号「」**（全仓统一弯引号 “”）。
   md 清单里用「」是既有做法、不受此限，照抄进 JSON 就 FAIL。
3. **`plan_card_rows` 不进提示词也不下发前端**——`render_pack()` 不消费它，
   `public_view()` 也不含它。所以这类错**修完线上零可观测差异**，不要据此怀疑
   部署没生效；反过来，它也确实没影响过任何一份已批出的批语。

另一条待定夺（**没改**）：`COUNTEREX` 正则 `不算|不是|算不上|不能算|不作数`
匹配不到「视为没抓住」「算未达成」，两课各误报一次 B12。改它会影响全部 14 包的
校验结果，不宜在补清单时顺手改。
