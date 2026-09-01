# Project Memory: laojohn-lesson-plan

> **索引维护规则（0818 立）**：① 新增课次/单本书状态 → 直接进末尾「已交付归档」聚合行，钩子 ≤20 字，不单独占行；② 新发现的横向通则 → 写进各线「跨课次通则」块，**不要埋进课次状态条目**（那样只有改那一课时才读得到）；③ 未决/交付风险 → 进「未决事项」块，做完即删；④ 行内不再标「必读」，优先级集中在各区头那一行；⑤ 索引超 15k 字符触发一次归档。

## 用户偏好
- 中文回复;简洁直接不堆砌客套;重要决策先列选项让用户拍板;视觉细节迭代频繁常用截图反馈
- **问「有没有做到X」时是要判断、不是指出问题**——先自己核查给结论,别把判断权反问回去

## 跨技能硬约束（三条详案线通用）
**动笔写任何详案前必读**：[约束分层](constraint-layering-generation-vs-coldreview-0804.md) · [机构课场景](venue-is-institution-not-school.md) · [真实情境官方锚点](real-situation-official-anchor-first.md)
- [约束分层:措辞层后移到冷审PassB(0804)](constraint-layering-generation-vs-coldreview-0804.md) — 判据=修这处要不要动教学设计;两线各建generation-brief;生成只读简报+正样本;冷审拆PassA结构/PassB行文各派fresh agent;⚠改规则文件勿破tone_gate四解析锚
- [分层改制首次实测:四项全过(0804)](layering-first-measurement-0804.md) — 二上第2次方法课冷启动生成;PassB七类36处(阈值8,贴线);**阈值暂不改等第二个数据点**
- [机构课·没有课本没有校内作息](venue-is-institution-not-school.md) — 「校内同步」只指跟教材进度不指地点;禁「翻开课本/晨读/课间」,教材图一律投屏;与[教室无黑板](classroom-no-blackboard.md)同族
- [真实情境先查官方锚点·兑现必须课内闭环](real-situation-official-anchor-first.md) — 别自造载体(标「已自含」的尤其);没有「下次课读上次稿」;承诺全班读到就得兑现
- [评价机制禁靠学生自报弱点(0803)](no-self-report-mechanisms.md) — 「说一声我是蒙的」实际没人会说,判定开关会空转;改客观结果自证
- [合集新亚型:有人物班底但无情节主线(0807)](collection-with-cast-no-plotline.md) — 比纯短篇集更易被误当长篇;建档须显式写「人物贯穿≠情节贯穿」+封死全书级工具;多出「辑内」中间层
- [0726全面审查修缮＋三项拍板(两写作线横向)](skills-audit-fixes-0726.md) — tone_gate机检门+组图编号/装置字段/60分钟弹性;改AI腔检核或两线checklist前必读

## 架构速览（骨架事实 · 细节在各 SKILL）
- 系统=老约翰深度阅读课件生成;工作目录 `E:\laojohn-lesson-plan\`;主链 lesson-plan(详案)→ppt-draft(中间稿+讲稿)→ppt(投屏pptx);writing-lesson/picture-writing/reading-assessment 为平行分支
- ppt 契约:6页型(封面/环节标题/引导问题/原文齐读/要点小结/填空表格)+7字段(眉标/标题/副标题/正文/要点/表格/配图建议)
- 每课时双产出中间稿.md+逐页讲稿.md页序1:1;P01=封面、正文P02起;页号唯一口径=中间稿P号==讲稿##第N页==详案页标〖PPT第N页〗==课件翻页;PPT不标页码角标
- 每节课独立PPT不合并;中间稿不写师话(线上系统无备注栏,师话→讲稿);眉标禁写课型;字体微软雅黑+宋体+Calibri零依赖;配图=占位框手动贴
- 换页点`【PPT换页-Pxx】`已废弃(分页权归ppt-draft;docx橙色渲染留作向后兼容)
- reading-guide 封面图取 `读书会书籍封面\<书名>.<ext>`(不带《》,与poster/book-card共用),找不到出占位、绝不联网编造
- **双人协作(0820立)**:项目已交接同事、两边都在产;同步分三层(源文件+记忆走git／版权插图与外部PPT走网盘／产物不同步各自重渲);**记忆已迁入仓库 `.claude\memory\`、用户目录那份是目录联接** — [详情](two-person-sync-0820.md)
- **目录口径(2026-07-23后)**:读书会线顶层目录全带「读书会」前缀;写作课件三目录+整套打包目录独立分线;旧名全部作废,详见 [bookclub-materials-dir-consolidation](bookclub-materials-dir-consolidation.md)

## 写作课（writing-lesson）
**写任何一篇前必读**：[⚠文风定盘·PassC已撤·判据缺AI痕迹半边](writing-style-two-directions-conflict-0831.md) · [教师自拟例子四判据](writing-lesson-example-must-be-unique-anchor.md) · [比喻反刻板+不绑老师真实生活](writing-lesson-metaphor-antistereotype.md) · [电报体/生造词红线](writing-lesson-telegraphese-and-coinage-redline.md) · 下方「跨课次通则」整块
### 跨课次通则（从课次经验抽离 · 写同类题目直接适用 · 展开见各源条）
- **开场姿态**：教具别编「本想做却没做成」的懊恼制造由头(学生看得出假),坦白说特意准备;凡用教具起头的课 — [源](guanchariji-4a-lesson-state.md)
- **官方情境在机构班不可兑现→把限制变成设定,不退回自造情境**:依赖「自带物品」的(四下《我的动物朋友》等)→实物不在场·稿子顶替;依赖「同班互相认识」的猜人反馈(四上《自画像》·六上《有你,真好》)→换掉「猜」保留内核,听众各说「看见的哪一处」 — [源1](xinaizhiwu-5a-lesson-state.md)/[源2](manhua-laoshi-5a-lesson-state.md)
- **「当场换人试装」装置**:念完自写段落当场换掉人名、余字不动再念,学生自己听出垮在哪;凡写人物特点/身份感的题目(写人·想象·故事新编·变形记)可照搬,配套成败标准「换上同桌名字故事一字不用改＝没写成」一并复用 — [源](woheguoyitian-4a-lesson-state.md)
- **外部件「示范文里的句子」类表格须逐行与示范文逐字比对**:截断可接受、**改写必须打回**;已四次出现 — [源](woheguoyitian-4a-ppt-chain-state.md)
- **往「禁止逐字复用」清单补串:一个串一条 bullet,不要并列写**——tone_gate 每条只取第一个「…」串,并列写的第二个串永不报警(实测画圈口令一篇内复发3处、机检全绿);清单运行时解析,补 bullet 即自动进机检、不必改脚本 — [源](twentyyears-hometown-5a-lesson-state.md)
- **教材换题＝重写不是改稿，且第 0 步是改事实源不是写详案**：新题在 `archive/` 零命中就动笔＝伪造官方条款；五处事实源连改（archive 旧节标停用·新节另起／index／course-map 题目行＋文体线链／锚点表／unit-texts **旧结论不变也要整节重写**，因判据「课文最突出的写法是不是正是本课这一招」里的「这一招」变了）；**文体线链一改，既有详案提纲表第 3 行会静默过期** — [源](wodejiaren-4a-lesson-state.md)｜**跨册迁移变体(0828《故事新编》四下八→五上三)**:改9处不是5处;教材题面与archive指导件是**两层**(指导件正文里根本没有题面内容,题面须单独入档);换题会让**判据表的实例**连带失效(C形态唯一实例没了);**多图对照别按给定顺序配标签**,用页码等图内锚反查(实测接反过) — [源2](gushi-xinbian-5a-unit-move-0828.md)
- **「倒过来写」指构思顺序、不指成文顺序**：本课差异轴与写人档降压铁律（第 2 节第一句先写点题中心句）表面相抵，用户拍板守铁律＋补出口——教的是「怎么想到这个特点」，不是「不许有中心句」；凡新技法与既有铁律冲突，先分清它管的是构思还是成文 — [源](wodejiaren-4a-lesson-state.md)
- **`参考：` 里的学生答案要过一遍「多数人家真会这样吗」**：编得巧但生活里不常有（「她炒糊一锅菜还说是故意炒的」），学生照着想不出对应的自家事，这一步就空转 — [源](wodejiaren-4a-lesson-state.md)
- **教材照片与联网核到的教参对不上时，称谓/数字/篇名这类逐字项须逐项复核，别一笔归为「版本差异」**：《我的家人》练书法那位被我录成「姥爷」（实为爷爷），教参本来是对的，却被「应为版本差异」这句结论连带盖住，错到详案 32 处才由用户抓出 — [源](wodejiaren-4a-lesson-state.md)
- **教材自带的提纲/范例＝必须落实的习作知识点，自创工具只能细化、不能顶替**：顺序「先教材框架→后自创工具→再回填」；同族坑＝否定反例须精确落到「缺了什么」，别扩大成「写了什么就错」 — [源](twentyyears-hometown-5a-lesson-state.md)
- **点名「可行做法」只点一种＝指定默认款**:覆盖面/支架/装置这类「硬要求但解法开放」的位置写清单不写单例,只有一种时显式标注「不是唯一」;不限于⑦位 — [源](writing-lesson-stage7-interaction-form-gap.md)

### 规则与体例
- [⚠文风定盘0831立·0901修正:判据缺AI痕迹半边](writing-style-two-directions-conflict-0831.md) — 润色方向仍是向规范书面靠(抒情句被保留);AI痕迹=破折号/导演腔/省主语/术语漂移;**PassC整篇重写已撤销别重开**(方向会反、被网页端完全覆盖);现行=判据`style-criteria.md`+执行位并入**PassB**;**护栏对+机检绿≠方向对**→新增`--baseline`方向指标,改写类工序跑完必看;**0901收敛定盘=一主三从**(主判据唯一源style-criteria·判据卡并入§六·benchmark降级正样本库·三分歧拍板念→读/短指令加请/术语门槛);修文件批量脚本必须**每步立即写盘**
- [横审报告曾被页标与_报告件淹没(0831)](batch-ngram-scan-pagemark-noise-0831.md) — 373→139条;页标带页码进不了白名单须正则剥;补白名单只收体例层不收师话;⚠逐字复用基线40已过时、实测48
- [教师自拟例子四条硬判据(0817)](writing-lesson-example-must-be-unique-anchor.md) — 连否四轮五次返工换来:**独一份**(嗓门大/不爱笑=通用款,会让课自相矛盾)／**夸张≠计数**(「问了八遍我们数过」不是放大)／**样板不得低于例句**／**一篇内锚点不复用**;判据在model-essay §四之四、管全篇例子不只示范文
- [比喻类写人反刻板＋示范材料不绑老师真实生活(0802/0817)](writing-lesson-metaphor-antistereotype.md) — 解法「先想只有他家才有的画面再找动物」须做成课堂明线;**两条全线通则:①例子不落到老师家人 ②默认措辞不强断言老师当下生活事实**(课案多人复用,「这是老师每天背的包」会逼老师说假话;授课提示是补救不是解法,须给替换清单+降级兜底)
- [③引本单元课文佐证技法·匹配则引(0821立)](writing-lesson-cite-unit-text-0821.md) — **并非每个单元课文都配得上习作主题,不配就不引、不许硬上**(三形态:阅读要素≠习作技法/课文是对象不是示范/方向相反,实证三上二·五上三);判据=有没有一篇「最突出的写法」正是本课这一招,沾边不算;判不引≠欠账、冷审不得逼补引;由「可引」升格;新建 unit-texts.md 事实源(仓内原本没有单元篇目、archive/course-map 设计范围都不含);**联网核实存量三处 3/3 全中,但「碰巧对」不是流程**故仍须先核实后落笔;CLAUDE.md §5 开第二个联网例外口;「没课本」与「引课文」冲突已定口径＝**禁指向动作不禁指代进度**
- [教学指令一律正向表述·写法只作对比不判对错(0824立)](writing-lesson-positive-framing-not-prohibition.md) — 禁令伤的是**照着上课的老师**(会形成「直接抒情=错误」认知并一刀切);判据先分两类(**写法偏好类**不判对错走三步对比、**题目要求类**照旧可判不合要求);五落点逐处查(提纲表核心技法行/③/④/⑥/**⑦最易漏**);**最主要复发路径=档案自己**(archive重难点常写成「避免笼统地说…」,那是给老师的教学重点不是课堂话术);与③「审题辨析」半步**不可合并**(那处比切题与否、有对错);三条反向刹车(减负性否定照写/教师可以有倾向/真实性格式硬要求不作对比);已落规则五处(红线第8条+workflow③+checklist C+rubric跨维八+brief);基准篇本就是正例、是固化不是新增负担
- [电报体/生造词红线第7条(0731立·0819补第5形态)](writing-lesson-telegraphese-and-coinage-redline.md) — 五形态自查(省主语/名词压缩/电报短语/生造词/**中心宾语残缺**);补宾语有反向刹车:术语只在定义句补一次,逐处补会撞池8配额;讲评括注直写动作、「占位」已升机检
- [师话必须接住上一轮真实产出(0803)](writing-lesson-shihua-must-follow-real-turn.md) — 假转折/假情境/假引文三变体;checklist·tone_gate·冷审三关全漏,只有通读语感抓得到
- [学段口气全线没分级(0817)](writing-lesson-grade-tone-not-differentiated.md) — 九篇③环节同构;**判断分三层(用词/技法深度/思维层级)别混说**;判据=降两级反问,改不动即没分级;已补technique-levels口气落地动作表+checklist C组+rubric第六节;**0828复发新形态**:档案重点是并列短语时只落实了好落实的那一半(「有趣合理」只教了合理),查法=把重难点按短语拆开逐个问落在哪个环节
- [新增「话轮骨架」层=池9+指纹第15字段(0817)](writing-turn-skeleton-layer-pool9.md) — 补零件层与措辞层之间的空档:③④⑦话轮序列;**冷审能打散措辞、打散不掉同构**;配 batch_ngram_scan 新增`--focus/--against`单篇邻篇机检(进checklist E组);⚠池9编号在后但属零件层
- [⑦交流评议连撞四人小组的根因(0817)](writing-lesson-stage7-interaction-form-gap.md) — 一推一放:F组「人人被听见」只点名小组内轮读、G组明说⑦不进跨篇避让;已改四处规则
- [技法N件套须练全N件](technique-set-practice-all-parts.md) — 少练的那一件学生动笔前零产出、⑦补不回来;定稿前做「每件×是否产出过」对账,机检与checklist都抓不到
- [开场钩子先行·单元交代后置(0801)](writing-lesson-opening-hook-before-unit.md) — 禁上来报「今天写第X单元习作」;先让学生有反应再自然点出
- [参考标签纪律+术语首现权+追问链](writing-lesson-label-and-turn-discipline.md) — `参考：`只装学生话;括号按「做/读」分家族
- [行文正样本+去AI味规则单边化根因(0804)](writing-lesson-prose-style-benchmark-0804.md) — 新建prose-style-benchmark.md(157行禁令/0段正例是根因);pools加「宁可重复不许自造」裁决序;短句占比INFO线13%;⚠方言词表已被实测否掉
- [导演腔第三层反同质化(池6/7)](writing-lesson-director-tone-antihomogenization.md) — 根因=生成侧金句写死;四层治理已验完
- [重建台账前先查缺指纹的篇(0819)](ledger-rebuild-drops-fingerprintless.md) — 四上两篇指纹曾被改稿顺手删掉,直接重建会静默抹掉它们那两行;先grep -L回写再重建
- [指纹块改14字段+装置粒度门槛](writing-lesson-fingerprint-fields-revised.md) / [横向生产+反同质化四项升级](writing-lesson-antihomogenization-upgrade.md) — 指纹会回读重建台账,装置判据=当场演过一件事;距离化避让/池5篇内规则/批次横审(⚠该条12字段说法已过时)
- [正文标点全角+方括号提示体例](writing-lesson-fullwidth-punct-bracket.md) / [语言风格红线覆盖后续改写](style-redline-covers-edits.md) / [交付前加通读语感扫](writing-lesson-naturalness-readthrough.md) — 去游戏化叫法+去形象比喻;checklist抓不到生造/别扭须纯语感通读
- [进阶线升全覆盖63任务+填空位必须全角＿＿(0802)](writing-progression-chain-full-coverage.md) — 总地图由md反向回写(全仓唯一);归线=文体首段·分档=册次;半角`____`会被docx引擎当加粗标记静默吃掉
- [文件名/目录名加「第N单元」段(0802)](writing-line-filename-unit-segment.md) — 全线标识改`<年级册>-第N单元-<题目>`(中文数字·取course-map单元列;自拟主题省略);⚠「PPT文件名内仍纯题目」那半条**0826已推翻**
- [写作课线三项命名/结构调整(0826立)](writing-line-naming-flattened-0826.md) — 配套件`-X合订`→`-X用`／打包目录**单层平铺**撤两层子文件夹／PPT改`<年级册>-第N单元-<题目>-课件PPT.pptx`(**推翻CLAUDE.md §7「PPT文件名内纯题目」**);⚠**pptx与anim.json必须同批改名**否则inspect_pptx防覆盖闸门静默失效、人工排的分组全废;⚠**Windows下glob返反斜杠、`rstrip("/")`是空操作**→basename得空串(取目录名一律用pathlib `.name`);**预演输出要逐行真看**(把丢了课次段的`→ -课件PPT.pptx`看成了列宽截断);打包脚本零删除逻辑故改结构必清存量;闸门=validate的E24＋shots.json的12条src逐条exists
- [标题与环节命名定稿](writing-lesson-title-naming.md) — 唯一源=references/title-naming.md;改体例前必全skill搜一遍
- [首页改无区头单表6行+两行文案体例(现行)](writing-lesson-front-page-single-table.md) — 0729定稿:删区头与「怎么落地」/课时回表/文体线→同类习作顺序;**0831两行体例二次改版(推翻0828):目标=一句话说清学会写哪一类文章(「通过…来学习怎么写…」或「掌握…;能…写成…」)、不写效果检验句;技法首句固定「使用“<构思工具名>”。」+平白两三分句,工具名须与正文一字一致;0828的破折号招名/旁批表/（辅：）三条停用;两行禁反例·备选·成果包装仍有效**;写详案或改style_front_page前必读(前身[分区版](writing-lesson-front-page-zones.md)、[两区表](writing-lesson-front-page-two-zones.md)已作废)
- [审题固化为③开头固定半环](writing-lesson-shenti-bianxi-fixed-half-step.md) / [第2节起步半环·L5–L6改判「定起点」+自由写作≥25分钟(0830)](writing-lesson-destress-onramp.md) / [修改符号自然用不重教](writing-lesson-revision-symbols-natural-use.md)
- [去先导预设/技法克制](writing-lesson-drop-prelude-preset.md) / [不引读书会书目](writing-lesson-drop-book-club-link.md) / [不写下游ppt提示标签](writing-lesson-no-downstream-ppt-hints.md)
- [详案出PPTX](writing-lesson-to-pptx.md) / [docx页眉定版](writing-lesson-docx-header.md) / [对标竞品待实施清单](writing-lesson-competitor-borrow-backlog.md) — 漏传--header-left/right静默回落读书会页眉;D3–D5/N1待做
- [作文批改工具(0818立项·0820出网页骨架)](writing-correction-tool-0818.md) — 给加盟商故**不能做skill**、移动端网页+**PWA只做manifest不做service worker**;判据从详案抽标准包JSON(「先看三条」是护城河);**错别字层原理上不能做**;`作文批改工具/web/`已跑通mock全流程,**真实链路已验(0820,定gpt-4o)**;**引用一字不差靠工程不靠提示词**(模型必改写原句→先出transcript再程序校正,拒绝的标suspect);thinking模型思考token计入completion(截断报错会指错方向);约束一收紧模型就躲进新模板;**批四层**(判据/整篇三项/亮点/focus,只有判据进档位),**治模式化靠focus不是靠加维度**;判断规则已收进build_prompt共用件、勿在服务端另写;**0821铺到14课全覆盖+固化抽取规程+补上线前三处**(首页流水式=标准包只有2个不是前端bug,先数json;「三条」在各详案指的不是同一样东西故只能通读判、写不了抽取脚本;四上修改收束多是反面条件式会让判据方向反,改取自由写作前的师话;bands键名必须归一否则汇总页三档全计0且不报错;一个包JSON坏掉整个服务起不来);**judge_by两条写法通则**(放宽类条款必须前置到判定最开头、写末尾100%不生效／判逐项齐不齐先让模型抄出来再数、否则笼统作答且说错事实并进家长点评卡);smoke_real不绑课可测任意课但不跑fix_quotes;**无密钥静默进mock是最危险的洞**(已加LJ_ENV=prod拒启);**0821加本机暂存**(IndexedDB24h,存压缩图不存原图、ok后连图也丢;四坑=sid做主键/24h按created不滑动/恢复前必校验mock否则点评卡丢水印/**S.seq取max(id)不能用length否则A的点评卡发给B家长**;探测超时必须3秒不能1.5秒,页面刚加载时事件循环被阻塞;**隐私口径从此两层**:服务端一张不留+本机存档,别再混成一句什么都不存;**当天又改成批语永久留+图只留一天**,加「以前批过的」可回看/重出点评卡/单课删,DB升v2;**文案一天改三次**,动前端存储策略要同步五处);**0826加版本徽章**(教材换题后新旧包并列,`edition{status,note}`,三坑=别塞topic/label否则进家长点评卡·必须补排序键否则旧题排前面且不报错·不进提示词);**0827补通用评价维度**(结构四项+语言两项;创意真情拍板不做;三件按不住的靠程序:三年级详略强制/口水词程序数/分段测不准标可疑)
- [批改工具已部署Vercel(0824)](writing-correction-tool-vercel-deploy-0824.md) — 项目laojohn-grader·真实批改已跑通(22秒);**入口必须是部署根index.py、绝不能放api/**(旧式文件路由会让所有/api/*路径塌缩成/api/index,症状是health返401+lessons返Not Found、指向完全错的方向);部署两步漏build_deploy.py不报错只是用旧判据;**Serverless下内存限额失效**改靠访问口令laojohn2026;max_image_mb已8→4(平台硬限4.5MB);**.vercelignore必须挡config.json**(CLI不看gitignore);**国内直连vercel.app完全不通**故备案不再是关键路径但国内可达性成头号风险(**手机流量实测待做**);正式地址grader.skyline666.top已挂CF;**DNS记录值别信CLI**(inspect给的A 76.76.21.21是旧文案,网页端Domains→View DNS configuration给的项目专属CNAME才是现行推荐,legacy值仍可用但会一直挂黄色警告);⚠本机已装node/npm/vercel CLI(还有openpyxl/pandas),**已据此订正CLAUDE.md §5**——重点是禁令风险性质变了:以前环境天然挡着违反不了、现在随时能违反,只剩纪律这层;**0824补齐核对清单14/14**(补的过程查出《写日记》plan_card_rows错误留空——根因是把「特点卡」当成构思表唯一形态,已修;三教训=**validate全绿证明不了包对**(可选字段留空不报错,藏了6天)／改包JSON会撞D20禁直角引号／该字段不进提示词也不下发前端故修完线上零差异、别据此疑部署没生效)
- [配套三侧削页+去逐字稿框架(0803)](writing-materials-pages-trimmed-0803.md) — 家长1页/教师2页;homework·feedback字段作废;教师侧禁「配合逐字稿·照本念」(grep要搜念|背稿|讲义);**⚠学生侧0818已回4页=加备用稿纸续页、非课后练笔页**
- [配套物料skill三侧全落地(建设史)](writing-materials-skill-student-bundle.md) — ⚠页数已被上条覆盖;_shared.py共享勿复制;家长侧禁虚构作品
- [手改只改HTML必被重渲冲掉(0821查实)](writing-materials-handedits-lost-on-rerender.md) — 0817修Type3那次重渲已实际冲掉一批手改文字且全程无提示;文字改动一律回写_data.json;判据=PDF文本比对同目录json措辞;只剩产物时用PyMuPDF show_pdf_page原位抠版式+insert_pdf补页(不动正文);⚠仓库内9课json仍不含那批手改
- **PPT 链**：[外部PPT须先读详案再审查再做动画(0806)](writing-ppt-review-against-detail-first.md)（链改四步+**已装机器闸门**,守做过不守全绿,机检全过≠审查完成,常反查出详案自身错、PPT对详案错勿迁就）· [改外部生成+本仓只做动画(0803)](writing-ppt-external-plus-animation.md)（build_ppt对写作课停用;讲稿页序改跟外部pptx;~~合一件叫`<题目>-全课`~~**0826改`<课次>-课件PPT`**）· [动画工作单填的是shape_id不是位置索引(0804)](ppt-anim-groups-are-shape-ids.md)（差2且范围重叠→静默绑歪整份;一律走regroup_anim.py+时间树反查）
  · **[手工动画会被注入器静默清掉+逐字对齐勿抄嵌套引号(0825)](manhua-laoshi-5a-ppt-chain-state.md)**（clear_timing在skip判断之前故skip页照清且不报警;详案单引号是嵌套降级、上屏须回升双引号而逐字校验必报True;页标回注后详案行号整体偏移、按行号取原文全错位）
  · **[外部件重复投放须先三项比对判重(0825)](external-pptx-duplicate-drop-0825.md)**（place_pptx按文件名认领会静默覆盖已处理件、动画与引号修正全丢;判据=文本块/媒体md5/形状几何全等即同源;重复件不归位、问用户删;真修订版重跑前须重跑audit_against_plan因页标回注已改详案md5）
- 历史条目(主体已废止,但夹带的规则仍有效别当垃圾删): [核心素养四维](writing-lesson-core-literacy-goals.md)(⚠四维节已取消;提纲表结构/不设任务背景节/H1体例仍有效) / [配套曾两轮清空](writing-materials-tools-removed.md)(已重建;仍有效=写作配套独立原则)

## 看图写话（picture-writing）
**排新课或出图前必读**：[总地图v5](picture-writing-course-map-v5-0728.md) · [角色口径](picture-writing-character-roster-policy.md) · [三图位两道硬门](picture-writing-three-image-slots.md) · [写规格的根因级判据](picture-writing-imgspec-writing-lessons.md) · 下方「跨课次通则」整块
### 跨课次通则（从课次经验抽离 · 排同类课次直接适用 · 展开见各源条）
- **课上不安排任何拼贴/剪裁/涂胶动作**(0805推翻背靠背贴):双面卡课前印好直接发,「先两看后两想」由**当堂翻面**承载;仍成立的那一半=发卡落点紧挨用卡那一步 — [源](picture-writing-2a-lesson3-state.md)
- **示范例文念两版**:先念只写已学、缺新学的那版让学生自己听出缺口,第二版才添;凡「在上一课例文基础上加写N处」的练习课 — [源](picture-writing-2a-lesson3-state.md)
- **凡详案写了「人人开口」,交付前逐环节数谁真开了口**(举手答/个别说/三人朗读都不算);可用解法=还本子时由「指着说」升成「读出声念给他听」 — [源](picture-writing-2a-lesson3-state.md)
- **表情类结果词禁令**:「露出上排牙齿」是结果词→无分界白块面且机器8/8全勾照过;**低龄欢快靠眯眼弯月＋腮红＋动作,干脆闭嘴笑最稳** — [源](picture-writing-1a-lesson2-state.md)
- **五官类返工一律回生成端改规格重出**,别在脚本`--edit`上耗轮次(已两次实测失效);image-spec「局部改可靠」说的是Gemini网页端,不可与脚本互相援引 — [源](picture-writing-1a-lesson2-state.md)
- **参考图带不住左右与地点**:辨识锚一律改位置式(「一只手腕上」),左右不作验收项、真承载教学时须用**画面方位**写死;组内同地点须逐件重写标志物 — [源](picture-writing-1a-lesson3-state.md)
- **出图两判据**:同类物件常态与异常会被合并(须拉距离＋各给颜色);改参考图一句否定顶不住、须正向逐项点名 — [源](picture-writing-2a-lesson3-state.md)

### 规则与体例
- [全64课主角角色口径已定(0804)](picture-writing-character-roster-policy.md) — 情境图课次必用班底+必填定妆参考(不填=放弃比例控制);44课角色已全表排定照取不自拟
- [总地图v5·0728重排期(现行)](picture-writing-course-map-v5-0728.md) — 24方法课次坐标全改+四问拆两问
- [一课三图位＋意外点两道选图硬门](picture-writing-three-image-slots.md) — 主图/练笔图/备选图必交齐(纯口头课不豁免);四问类主图无意外点=一票否决
- [写图位规格的根因级判据](picture-writing-imgspec-writing-lessons.md) / [朝向类必须写四件几何](picture-writing-orientation-must-be-geometric.md) — 约束身体朝向非脸朝向,可数元素锁总数+位置+禁别处;「看着X」须写转角+瞳孔+连线+高度,只写结果必偏;**判据躺在经验区就等于没有**(已提进image-spec §A模板)
- [B级链+比例唯一控制点=定妆图(0730四轮)](picture-writing-b-level-char-ref-landed.md) — 主图写`定妆参考:角色名`即带定妆图;**比例只能靠改定妆图调**(提示词写数值/写禁令双双实证无效,死措辞勿加回);PS缩头已成立、四张母版已换;A级锚图链已摘除
- [生图画风靠锚图参考图锁定](picture-writing-image-style-lock.md) / [画风收全局两档令牌](picture-writing-global-style-tokens.md) — 形容词控不住画风,机器验收判不出季节/背影;现行**三处**令牌须一字一致(条内"两常量"已过时);厚涂改造已终止勿重启
- [角色册已落盘assets+定妆图收口](picture-writing-character-sheet-landed.md) — 事实源=assets/角色册/角色设定.md(根目录0728第一部分作废)
- [详案输出改「一课次一目录」(0803)](picture-writing-detail-dir-per-lesson.md) — 四件收进课次夹;**图位路径未变**故存量取图口径不受影响;image_dir旧布局回落分支不可删
- [详案标题三行体例](picture-writing-title-naming.md) / [提纲页行名改教研通用词(两线)](outline-row-names-teaching-terms.md) — 主题式H1+`######`期次副标(脚本判型认副标行);七行新名=style_front_page PROFILES键,改md必同步脚本
- [首页定版三区提纲页](picture-writing-front-page-3zones.md) / [首页删四维目标节](picture-writing-opening-simplified.md) — 三区一张表+语义灰阶无红,`（本课）`标记必留;目标由提纲表+各课时「本课目标」承载,style_front_page.py必跑
- [骨架分A/B两层工作流](ability-ladder-AB-layer-workflow.md) / [ability-ladder索引三个坑](ability-ladder-index-reading-pitfalls.md) — A约束层详案前定、B实施层定稿后回录只抄不设计;状态列≠已产出,冲突以course-map为事实源
- [去AI味五类语言肌理规则](deai-language-rules-solidified.md) — 规则=lesson-structure §13+checklist+rubric;判据=读出声像不像真老师顺嘴讲
- [0804审计docx落地+立正样本+§13.10](picture-writing-prose-style-benchmark-0804.md) — docx意见只落地一半(有牙齿的才被执行);§13.6曾被降级已回正;⚠二上两篇已失效勿改;⚠短句占比在本线不可用作筛查线
- [三课冷审落定＋六类生成侧毛病](picture-writing-cold-review-round-0726.md) / [已接入detail-review冷审](picture-writing-cold-review-wired.md) — 交付前按七类自查;冷审B块建议不照单全收;第三份review-rubric+判型信号【图位:/imgspec;改图位规格须回验真图
- [「细节四方向」→「细节四问」](picture-writing-sifang-renamed-siwen.md) / [两项全仓术语统一](terminology-unified-image-and-model-essay.md) — 期6编号不变、计数以「问」计;下水文→示范文、锚图→主图
- [附录两节包注释不进docx](picture-writing-appendix-comment-wrap.md) — 生图工单/真实性自检整区包`<!-- -->`;正文禁悬空转引
- [配套物料skill落地](picture-materials-skill-created.md) — 四件A4印刷件;薄shim复用writing _shared.py;家长页禁虚构学生作品
- [起步档教学深度补厚](picture-writing-qibu-teaching-depth.md) / [旧5期经验萃取](picture-writing-legacy-extraction.md) / [生成侧收归本地](picture-writing-generate-locally.md) — lesson-structure §2分层追问链+逐句扩句示范;方法性经验已收八成别重复劳动;SKILL/references只有本地一个源
- [一上第1次回填定妆参考并重出(0803)](picture-writing-1a-lesson1-char-backfill.md) — 存量还债第一例;三条连带=旧主图是画风锚须先移存/topic-registry先填后改/回插件不跑style_front_page;给存量课次回填前必读
- 历史条目(排期口径已被v5覆盖,工程事实仍有效如`【图位:编号】`占位硬契约与insert_images finditer修复): [总地图v4](picture-writing-course-map-v4-0723.md) / [v6升24期](picture-writing-24-stages-v6.md) / [总地图v3](picture-writing-course-map-v3.md) / [20期制](picture-writing-20-stages-expansion.md)

## 读书会详案（lesson-plan）
**写详案前必读**：[逐环节装载量双向核查](lesson-plan-per-step-load-audit.md) · [创意环节正向标准三件套](lesson-plan-positive-standard-over-negative.md) · [环节标题三段式](lesson-plan-step-title-format.md)
- [环节标题＝功能·内容三段式(0807)](lesson-plan-step-title-format.md) — L2四本曾集体只写内容式标题已回补;功能名≤10字、同课时内不重复;规则在style-and-format+checklist
- [一节讲不完的根因](lesson-plan-lesson-total-load-fit.md) / [创意环节防平庸=正向标准三件套](lesson-plan-positive-standard-over-negative.md) — 课堂动作量必须按标称配时倒算;只堆负向约束→模型取平庸下限
- [逐环节装载量双向核查](lesson-plan-per-step-load-audit.md) / [三类文本差异化](lesson-plan-three-text-type-focus.md) — 过挤过松都查,≥5分钟环节须有学生动作;名著优先·三选一互斥
- [详案偏薄根因=师话密度低](lesson-plan-shihua-density.md) — 三杠杆补厚(师话写长/参考填实/原文精读用足)
- [导读钩子要切题](lesson-plan-hook-must-fit-theme.md) / [预测锚点须是已读内容](lesson-plan-prediction-anchor-must-be-read.md) / [导入钩子须先声夺人](lesson-plan-intro-hook-must-grip.md) — 禁次要情节线做钩子;禁剧透后猜已知答案,钩子埋了要兑现;根因=全负向缺正向标准+没盘点素材
- [导读课开场话术反同质化](lesson-plan-opening-antihomogenization.md) / [跨书查重防工具套路化](lesson-plan-cross-book-dedup.md) — 示范句禁逐字照抄、避「先不急着/先不忙」前缀家族;同一工具连用两本即换型
- [学生课前已人手一本书](students-already-have-book.md) / [教室无黑板白板](classroom-no-blackboard.md) / [详案禁ASCII图用表格](lesson-plan-no-ascii-diagram-use-table.md) — 禁「说出书名之前」类假悬念;禁板书改学习单(检索黑板/板书/白板应零);工具一律MD表格
- [思维工具讲解从简](lesson-plan-tool-intro-concise.md) / [师话比喻须配得上学段](lesson-plan-metaphor-age-fit.md) — 禁标「首次出现」,判据=结构绕不绕;比喻判据「给三年级讲是否一模一样」
- [SKILL通读审计A–D闭环](lesson-plan-skill-audit-fixes.md) / [阅读计划表不算可视化工具](reading-plan-not-vistool.md) — 判据数字唯一源=checklist;checklist与rubric有意重叠不得互删
- [详案复盘冷启动化](detail-review-cold-start.md) / [复盘三文件去冗余](review-rubric-single-source-dedup.md) — 派fresh子agent冷审;review-rubric是五维/协议唯一源
- [PPT链产出后详案页标回注必做](ppt-draft-pageback-mandatory.md) / [ppt-draft参考答案上屏从宽](ppt-draft-reference-answer-generous.md) — 〖PPT第N页〗必做并重渲docx(docx常被WPS锁须先关)

## 建档（book-profile）
**给任何书建档前必读**：[全文通读红线](book-profile-full-read-redline.md) · [插图前置到建档阶段](book-profile-read-images-during-profiling.md)
- [建档必须全文通读(红线)](book-profile-full-read-redline.md) — 严禁框架/选读代替;骑鹅框架式建档实测出三硬伤
- [插图前置到建档阶段(0806)](book-profile-read-images-during-profiling.md) — 通读时同步逐张目视,图单前置+档案加`## 十、原书插图`指针节(两份模板一起改);**角色归属须锚定原文句,锁不住写「未定」**;三坑=文件名编号≠正文顺序·同幅判定不能只信哈希·判读矛盾要放大
- [图单判读四类失败模式(0807)](illustration-judgement-failure-modes.md) — 存盘方向错→强咬合图变废图;「目视更正」会再错一次;颜色须对着背景判;人工核对结论不写回图单＝没核;⚠页码压画面交人工别用脚本
- [可引用原文栏取成段](book-profile-quote-full-passage.md) / [类型字段禁空泛「儿童小说」](book-type-no-generic-children-fiction.md) — 下游需成段并保留原书弯引号;类型须具体文学类型
- [低段/合集建档差异](low-grade-collection-profile-formalized.md) — 区分变量是「低段」非「快乐读书吧」
- [SKILL状态](book-profile-skill-state.md) — 黄金样例=洞;俗世奇人档案已重建

## 引擎与下游物料
**碰引擎/共享件前必读**：[下游六件抽共享层](downstream-shared-layer-and-token-facts.md)（改真源照该条回归法）· [0727上下文瘦身收官](context-engineering-slimdown-0727.md)（细节已下沉references别抄回）
- [宣传件渲染链+PDF反查源三指纹(0826立)](promo-materials-render-chain.md) — 家长端海报误判「无源」手改一次,代价=体积391KB涨到12.8MB+文字层乱序(源其实一直在、只是叫「招生海报.html」);**反查三指纹**=页宽÷0.75去grep html宽度/producer分Skia(脚本渲)与Chrome(手工另存)/内嵌字体与图像数;新建根目录`render_promo_html.py`(PROFILES表,tall与fixed两模型,馆内海报scale必须0.98);**海报html已改为入库**(自包含源、重渲不出来),不放行则同事只有旧pdf没有源
- [配套PDF的Type3字体病已修两线(0817)](pdf-type3-fonts-fixed.md) — 根因=雅黑字表外字符触发系统回退、编辑器拒编;装饰图标改纯CSS图形非换emoji;`.mark .sym`字体栈中间那档雅黑勿删;已装check_type3
- [下游六件抽共享层+token账实测](downstream-shared-layer-and-token-facts.md) — 合并skill省不了token(skill仅占常驻19%);三条真源+薄壳;改真源照该条回归法(PDF比字节数不比md5)
- [0727上下文瘦身收官](context-engineering-slimdown-0727.md) / [docx引擎标题层版式](docx-engine-title-heading-layout.md) / [引擎冗余审计](docx-engine-redundancy-audit.md) — 细节已下沉references别抄回;PLAYWRIGHT口径以此为准;评估过拆三脚本→不拆别再重复排查
- [两个常驻文件的分层重构(0818)](memory-index-structure-over-size-0818.md) — 常驻仅占窗口2.5%故**别再拿字符数当优化目标**;MEMORY.md真病灶=单课次状态占64.6%·必读通胀·**通则被埋在课次条目里**(⚠重构后字符反增4.5%,通则上浮是有意净投入);CLAUDE.md降12.2%且**判据=共享脚本docstring才是细则天然唯一源、比references更好**(下沉前先head -20,多半是纯重复可直接删);已修templates路径错+README↔§7双向循环指针;改这两个文件前必读
- [读书会详案原书插图链路(0730)](lesson-plan-book-illustration-chain.md) — 新顶层`读书会原书插图\<书名>\`(图不入库·_图单.md入库)+回插件升共享件PROFILES;详案写`【图位:插-01｜图注】`禁`![]()`;⚠PROFILES字段的CLI默认值一律None(硬默认静默盖档);PPT与阅读单吃图未做
- [fix_quotes会毁代码块里的命令(0807)](fix-quotes-breaks-code-blocks.md) — 无差别替换不认```,粘出去的bash直接跑不了且check_quotes也不报;含命令示例的md跑完须回扫代码块还原半角
- [Bash heredoc写文件六坑(0820立·0821补三条)](bash-heredoc-file-writing-pitfalls.md) — **定界符漏引号→反引号被shell执行成空、脚本照报成功**/中文别手写unicode转义(已两次打错字)/读写不带newline=''会把CRLF换成LF(diff炸全文但git只认真实改动);超长静默截断(≤90行一块)/`
`被折成真换行(用chr(92)拼)/替换失败前先grep数次数别默认没写入;三者报错都指错方向
- [Write吞弯引号→必跑fix_quotes](write-tool-normalizes-curly-quotes.md) / [下游JSON引号统一弯引号禁「」](json-materials-curly-quotes.md) / [雅黑弯引号显示半角](curly-quotes-render-halfwidth-yahei.md) — 含引号段落Edit改用无引号锚点;存量4本已改;字符层U+201C已对别改JSON,靠模板unicode-range落宋体
- [桌面插图批量去豆包水印管线](doubao-watermark-removal-pipeline.md) — 两批106张已交付;脚本dewatermark_batch.py在记忆目录;方位判定只能用参考模板形状匹配、输入glob必须排除产物
- **PPT 引擎**：[新增第三个profile宣讲(0824)](ppt-promo-profile-0824.md)（对外宣讲件47页16:9;分派点改PROFILES查表顺带修掉「文体写错静默落回读书会」;**四个静默坑**=封面/环节标题两名字不可改·要点块裸行被丢弃·多图只能走`场景：`·add_image_cover放文档截图必裁;版式溢出机检查不出来）· [按profile分层](ppt-profile-seam-architecture.md)（呈现层分reading/writing、底层原语不fork;Phase3待办）· [中文变Calibri修复](ppt-font-ea-latin-order.md)（根因OOXML字体槽latin须在ea前）· [表格自适应](ppt-table-autofit.md) / [原文齐读超长自适应](ppt-quote-autofit.md)（存量pptx重烘才生效）· [阅读单页型已下线](ppt-reading-sheet-page.md)
- **PPT 视觉**：[副标题克制电报体](ppt-subtitle-no-telegraphese.md) / [参考答案红字上屏](ppt-reference-answer-on-slide.md) / [逐条点击动画](ppt-click-reveal-animation.md) / [四图网格](ppt-four-image-grid.md) / [逐页讲稿新增docx](lecture-notes-docx.md) — 末条:打包只收docx
- **工程坑**：题目带全角＿＿则 `place_pptx` 必认领失败、须手工归位；配图空占位机检查不出、须肉眼看 —— 出自 [woheguoyitian-4a-ppt-chain-state](woheguoyitian-4a-ppt-chain-state.md)
- [阅读单skill固化](reading-sheet-skill.md) / [模板库扩到18个](reading-sheet-template-expansion-18.md) / [默认同出PPTX](reading-sheet-always-pptx.md) / [原生可编辑PPTX](reading-sheet-editable-pptx.md) / [不打ZIP要合订PDF](reading-sheet-no-auto-zip.md)
- [鱼骨图改竖纸+内容旋转90°](reading-sheet-fishbone-landscape.md) / [维恩图改双长椭圆](reading-sheet-venn-ellipse-rewrite.md) — 真横向纸只有timeline,改几何只动#canvas内坐标并同步render_pptx;等大椭圆⇒独有区宽度恒定别改回固定x
- [测评卷SKILL状态](reading-assessment-skill-state.md) / [测评事实以详案为准](assessment-facts-follow-lesson-plan.md) — 「遮书能猜」根因=正确项唯一显眼,详案升深度蓝本(事实仍锁档案);与SKILL默认相反,遇分叉先确认
- [阅读指南拓展栏点名具体书/影片](reading-guide-extension-concrete-titles.md) — 仅此栏放宽红线,吃不准就不写
- [目录口径大改名已收官](bookclub-materials-dir-consolidation.md) — 读书会线顶层目录加前缀、两线课件目录拆分

## 未决事项与交付风险（做完即删）
- **⚠ 神笔马良 插-24 页码未裁，不得对外交付** — [详情](shenbi-maliang-lesson-plan-state.md)
- **⚠ 阅读单线 18 份 PDF 的 Type3 字体遗留未修** — [详情](pdf-type3-fonts-fixed.md)
- 彼得·潘档案 line23/32 与机读块不一致待清理 — [详情](peterpan-book-profile-state.md)
- 封面图缺（汉修先生 / 呼兰河传 / 骑鹅旅行记，骑鹅须补图重跑）· 快乐王子下游未做 · 快乐读书吧 6 本已建 2 本余 4 本
- **⚠ 四下第八单元现行习作待核实**——定了才能改 63→62、序 32 回填、馆内海报两格重渲;`assets` 总地图 docx 原件尚未换版(**全仓唯一 md 先于原件**) — [详情](gushi-xinbian-5a-unit-move-0828.md)
- 《推荐一个好地方》两处详案↔PPT微差未拍板 · writing 竞品借鉴 D3–D5/N1 待做 · ppt-profile Phase3 待办
- **⚠ L5–L6 起步半环 0830 改判「定起点」后，存量 6 篇五年级稿未回改**（自由写作 19–24 分钟，均低于 25 分钟新下限；其中《缩写故事》19 分钟属篇幅例外）— [详情](writing-lesson-destress-onramp.md)

## 已交付归档（细节各见链接 · 排新课次前按需打开）
**读书会 · 书籍**：[快乐王子L5](kuailewangzi-lesson-plan-state.md)/[建档](kuailewangzi-book-profile-state.md)（童话集9篇无主线·篇名不可换通行译名·无页码）· [独一无二的伊凡](yifan-ppt-chain-state.md)（全链路已齐·中间稿兼任ppt-draft正例）· [玛丽阿姨建档](marypoppins-book-profile-state.md)/[全链路](marypoppins-lesson-plan-state.md)（纳翰应为约翰·玛丽对奇事一律否认）· [彼得·潘建档](peterpan-book-profile-state.md)/[L4全链路](peterpan-lesson-plan-state.md)（正文与附录是两个文本不可混）· [汉修先生L3](hanxiu-lesson-plan-state.md)/[建档](hanxiu-book-profile-state.md)（书信日记体·八个转折点串主线）· [呼兰河传L6](hulanhe-lesson-plan-state.md)（群像缀连·两副面孔对照表）· [俗世奇人](suishi-qiren-lesson-plan-retested.md)（「死鸟·贺道台」是姓+官职非本名）· [骑鹅旅行记L6](qie-lvxingji-lesson-plan-state.md)
**读书会 · L2/L3 合集批（0806–0807）**：[神笔马良详案+配图](shenbi-maliang-lesson-plan-state.md)/[建档](shenbi-maliang-book-profile-state.md)（存量书按0806新规补做第一例·9图落点全换·角色不跨篇）· [孤独的小螃蟹详案](guduxiaopangxie-lesson-plan-state.md)/[建档](guduxiaopangxie-book-profile-state.md)（首个建档时同步读图·两篇结构不同·跨行断裂别当错字改）· [小狗的小房子详案](xiaogou-xiaofangzi-lesson-plan-state.md)/[建档](xiaogou-xiaofangzi-book-profile-state.md)（第二篇残缺标节选但不对学生说「没结局」）· [大头儿子和小头爸爸详案](datou-erzi-lesson-plan-state.md)/[建档](datou-erzi-book-profile-state.md)（24篇四辑·**有班底无主线**故禁全书成长曲线·画文冲突11/17幅）· [克雷洛夫寓言建档L3](kryluov-book-profile-state.md)（71则·**寓意三形态**·同名角色不跨篇·47篇无图）· [稻草人建档L3](daocaoren-book-profile-state.md)（12篇零共同角色·**电子版三处串行错乱禁逐字引**）
> 这批的共同教训：**事务性话术是跨书查重高发位**（第2课时开场骨架已四本连用）；下一本 L2 的开场/预测单/送卡三形态必须换。
**写作课 · 详案**：[三上续写故事](xuxie-gushi-textbook-image-rewrite.md)（改用教材真图+新建教材插图目录）· [三上我来编童话](bianTonghua-3a-lesson-state.md)· [三上写日记](xieriji-3a-lesson-state.md)（例句池三处联动）· [四上写观察日记](guanchariji-4a-lesson-state.md)（三杯不同天数真豆子·⚠须沥干湿布捂养）· [四上我和＿＿过一天](woheguoyitian-4a-lesson-state.md)· [五上我的心爱之物](xinaizhiwu-5a-lesson-state.md)（开场道具·③装置·示范文是同一件东西须三处同步）· [五上“漫画”老师](manhua-laoshi-5a-lesson-state.md)（三处同一例须同步）
· [五上二十年后的家乡](twentyyears-hometown-5a-lesson-state.md)（**0827依教材页原件重写**：教材提纲被自创表顶替／猜年份误当合格门槛／「跑题」误判＋详略情感补齐；正向对比首份实践·课文判不引形态A）
· [四上我的家人](wodejiaren-4a-lesson-state.md)（**2026秋教材换题首例·替代小小动物园**；写人线差异轴必须反转「事→特点」因三下已教完「特点→事」；教材气泡当公共素材源破「不拿老师家人举例」；四坑＝引教材原句擅自加词废掉后续演示／③剧透④指向性问题／审题辨析与示范文须投屏否则「回头数一数」做不到／提纲表核心技法行是正向表述最易漏的落点）
**写作课 · PPT 链与配套**：[四上推荐一个好地方](tuijian-haodifang-4a-ppt-chain-state.md)· [四上写观察日记](guanchariji-4a-ppt-chain-state.md)（**二维构思表转置法**·教师侧压页合并heading比删行管用）· [四上我和＿＿过一天](woheguoyitian-4a-ppt-chain-state.md)· [四上小小"动物园"](xiaoxiao-dongwuyuan-4a-ppt-chain-state.md)（**教材已换题停用，产物原地保留**；含删重复段按行切片、直引号批量转弯引号两条可复用，与教材无关仍有效）· [五上我的心爱之物](xinaizhiwu-5a-ppt-chain-state.md)（文件名中文丢成下划线的认领法·旁批表引用第四次被改写）· [五上“漫画”老师](manhua-laoshi-5a-ppt-chain-state.md)（进仓叫00000.pptx靠封面认领·图例保留改人工加动画）
**看图写话 · 课次**：[期6细节四问(二上第1次)](picture-writing-stage6-state.md)（例-01季节违规重生教训·先生锚图再生例库图才锁画风）· [二上第2次](picture-writing-2a-lesson2-state.md)（节2整节评改升格）· [二上第3次](picture-writing-2a-lesson3-state.md)（`**`在配套模板不解析只认`{b}`·页数核验只测第1个sheet）· [一上第2次](picture-writing-1a-lesson2-state.md)（全线首个无主图课次·generate_images已加无主图兜底·「上次约定」入师话须回查原话）· [一上第3次](picture-writing-1a-lesson3-state.md)（首个多格课次·**C级链首验成立→18个多格课次可直接排**·docx「半角标点」警告是误报勿改）
