# Project Memory: laojohn-lesson-plan
> **索引维护规则(0818立·0901补)**:①新增课次/单本书状态→进[归档索引](memory-index-archived-deliveries.md),不占索引行;②横向通则→各线「跨课次通则」块,不埋进课次条目;③未决/交付风险→「未决事项」块,做完即删;④优先级集中在各区头行;⑤行数≤150、单条钩子≤200字符、细节下沉主题文件,超限先归档,机检挂SessionStart hook自动跑;⑥CLAUDE.md只写现行规则,来历/日期/旧口径进记忆;压缩前快照=[0911-2](memory-index-archive-20260911-2.md)
## 用户偏好
- 中文回复;简洁直接不堆客套;重要决策先列选项让用户拍板;视觉迭代常用截图反馈
- **问「有没有做到X」时是要判断、不是指出问题**——先自己核查给结论,别把判断权反问回去
## 跨技能硬约束（三条详案线通用）
**动笔写任何详案前必读**：[约束分层](constraint-layering-generation-vs-coldreview-0804.md) · [机构课场景](venue-is-institution-not-school.md) · [真实情境官方锚点](real-situation-official-anchor-first.md)
- [约束分层:措辞层后移到冷审PassB(0804)](constraint-layering-generation-vs-coldreview-0804.md) — 判据=修这处要不要动教学设计;生成只读简报+正样本;冷审PassA结构/PassB行文各派fresh agent;⚠改规则文件勿破tone_gate四解析锚｜[首次实测四项全过](layering-first-measurement-0804.md)
- [机构课·没有课本没有校内作息](venue-is-institution-not-school.md) — 「校内同步」只指跟教材进度不指地点;禁「翻开课本/晨读/课间」,教材图一律投屏;与[教室无黑板](classroom-no-blackboard.md)同族
- [真实情境先查官方锚点·兑现必须课内闭环](real-situation-official-anchor-first.md) — 别自造载体(标「已自含」的尤其);没有「下次课读上次稿」;承诺全班读到就得兑现
- [评价机制禁靠学生自报弱点(0803)](no-self-report-mechanisms.md) — 「我是蒙的」没人会说,判定开关空转;改客观结果自证｜[合集新亚型:有班底无情节主线(0807)](collection-with-cast-no-plotline.md) — 「人物贯穿≠情节贯穿」+封死全书级工具;多出「辑内」层｜[0726审查三项拍板](skills-audit-fixes-0726.md) — 改AI腔检核/两线checklist前必读
## 架构速览（骨架事实 · 细节在各 SKILL）
- 主链与平行分支见 CLAUDE.md §2｜每课时双产出中间稿+讲稿页序1:1;页号唯一口径=中间稿P号==讲稿##第N页==详案页标〖PPT第N页〗;PPT不标页码角标;中间稿不写师话(师话→讲稿);眉标禁写课型
- **双人协作(0820)**:口径见 CLAUDE.md §9;记忆事实源=仓内 .claude/memory/,用户目录那份是目录联接;看板与commit前缀0911已取消 — [详情](two-person-sync-0820.md)
- **skill停用归档0910立·0911撤回**:只省description 2.8k字符(窗口0.2%),误触发方向反;22个全部在架,别再重做;活线两处查找与gitignore skills*通配保留无害 — [详情](skills-parked-0910.md)
## 写作课（writing-lesson）
**写任何一篇前必读**:[0911换靶](generation-retarget-0911.md) · [文风定盘](writing-style-two-directions-conflict-0831.md) · [例子四判据](writing-lesson-example-must-be-unique-anchor.md) · [比喻反刻板](writing-lesson-metaphor-antistereotype.md) · [电报体红线](writing-lesson-telegraphese-and-coinage-redline.md) · 下方「跨课次通则」整块
### 跨课次通则(写同类题目直接适用 · 展开见各源条)
- **开场姿态**:教具别编「本想做却没做成」的懊恼由头(学生看得出假),坦白说特意准备 — [源](guanchariji-4a-lesson-state.md)
- **官方情境在机构班不可兑现→把限制变成设定,不退回自造情境**:自带物品类→实物不在场稿子顶替;同班互认的猜人反馈→换掉「猜」保留内核 — [源1](xinaizhiwu-5a-lesson-state.md)/[源2](manhua-laoshi-5a-lesson-state.md)
- **「当场换人试装」装置**:念完当场换人名再念,学生自己听出垮在哪;写人物特点/身份感的题目可照搬,成败标准「换名字一字不用改=没写成」一并复用 — [源](woheguoyitian-4a-lesson-state.md)
- **外部件「示范文里的句子」类表格逐行与示范文逐字比对**:截断可接受、改写必须打回;已五次出现(0902第五次:改示范文必连查同篇表格列) — [源](woheguoyitian-4a-ppt-chain-state.md)
- **往「禁止逐字复用」清单补串一个串一条bullet**:tone_gate每条只取第一个串,并列写的第二个串永不报警;清单运行时解析补bullet即进机检 — [源](twentyyears-hometown-5a-lesson-state.md)
- **教材换版(题目没变、题面/课文换掉)=第三形态,连改9处但course-map与文件名全不动**:三上四单元实做;教师侧配套2页是硬闸门,示范文变长须回压旁注 — [源](textbook-revision-same-title-new-page-0902.md)
- **教材换题=重写不是改稿,第0步是改事实源**:archive零命中就动笔=伪造官方条款;五处连改(archive/index/course-map/锚点表/unit-texts);文体线链一改既有详案提纲表第3行静默过期 — [源](wodejiaren-4a-lesson-state.md)｜跨册迁移改9处不是5处;题面与指导件是两层 — [源2](gushi-xinbian-5a-unit-move-0828.md)
- **「倒过来写」指构思顺序不指成文顺序**:新技法与既有铁律冲突,先分清管构思还是成文 — [源](wodejiaren-4a-lesson-state.md)｜**`参考：`里的学生答案过一遍「多数人家真会这样吗」**,编得巧但生活不常有=空转 — [源](wodejiaren-4a-lesson-state.md)
- **教材照片与教参对不上时,称谓/数字/篇名逐项复核**,别一笔归为「版本差异」;以用户最新教材为准,改前先问 — [源](wodejiaren-4a-lesson-state.md)
- **教材自带提纲/范例=必须落实的知识点,自创工具只能细化不能顶替**;否定反例精确落到「缺了什么」 — [源](twentyyears-hometown-5a-lesson-state.md)
- **点名「可行做法」只点一种=指定默认款**:硬要求但解法开放处写清单不写单例 — [源](writing-lesson-stage7-interaction-form-gap.md)
- **自由写作页固定按两页写页码**(教师每次自插一页学生稿纸截图);区间页标`第23-24页`引擎不认须单号＋括注 — [源](writing-freewrite-two-pages-0911.md)
- **某节超时先砍重复不砍步骤**:同一材料读两遍/同一功能两处落点是首选压缩位;标称配时对齐逐环节实估、别平均摊(0907故事新编①②④富余2.8全压在③⑤) — [源](lesson-timing-overrun-cut-repeats-not-steps.md)
- **示范文的可数断言（共几段/哪段最长/只用两三句）必须脚本实测**:意图与成品会漂移,通读看不出、学生一数就露;优先压示范文不优先改师话;⚠冷审改完须复跑机检(新写的师话会带回刚删的毛病) — [源](model-essay-countable-claims-must-be-measured.md)
- **换掉/改长教师示范文=四处下游连改**:详案12处/配套两侧json/批改标准包进提示词/PPT六类页外部重做;须回看③反例是否撞车;⚠变长还会顶爆配套页数闸门 — [源](model-essay-swap-downstream-chain.md)
### 规则与体例
- [示范文规则0912补五条+机检E+瘦身](model-essay-rules-supplement-0912.md) — 够得着上限=优等学生;旁批表最见功夫两句必入表;不教第四招;起笔不与③反例同型;§六第7问;essay_audit.py每份必跑;⚠已拆条文+history,生成只读顶部一屏卡,别把来历写回条文
- [张祖庆视角接入写作课线(0912)](zhang-zuqing-on-writing-line-0912.md) — 三处落位:生成侧generation-brief§一.8减法三问/冷审rubric跨维九+维三三问/示范文链;体系审计8条已拍板采5不采3(讲评按需·审题依需·三档表);话语比不能当判据;三档优先级标记不推广
- [⚠0911换靶:生成侧语体=规范教案·瘦身41%来历下沉·polish_writing机械层·PassB四个不执行机制](generation-retarget-0911.md) — 生成只读简报§一.7+prose-exemplars;避让卡替代整读pools/ledger;A/B待做
- [⚠文风定盘0831·0901收敛一主三从](writing-style-two-directions-conflict-0831.md) — 方向=向规范书面靠;AI痕迹=破折号/导演腔/省主语/术语漂移;**PassC已撤别重开**;主判据唯一源style-criteria+执行位在PassB;改写工序跑完必看--baseline方向指标;批量修文件脚本每步立即写盘;⚠方言词表已实测否掉勿加回
- [配套三侧文案0901起桥接style-criteria](writing-materials-style-bridge-0901.md) — 此前只有0803单边去AI腔、方向反;SKILL红线拆两条+§四认领+§二.1回填8对;picture-materials仍真空(补时桥它自己线§13)
- [横审报告曾被页标淹没(0831)](batch-ngram-scan-pagemark-noise-0831.md) — 页标须正则剥;白名单只收体例层;⚠逐字复用基线40已过时实测48
- [教师自拟例子四条硬判据(0817)](writing-lesson-example-must-be-unique-anchor.md) — 独一份/夸张≠计数/样板不低于例句/一篇内锚点不复用;管全篇例子不只示范文
- [比喻类写人反刻板+示范材料不绑老师真实生活(0802/0817)](writing-lesson-metaphor-antistereotype.md) — 「先想只有他家才有的画面再找动物」做成课堂明线;例子不落老师家人;默认措辞不强断言老师当下生活事实
- [③引本单元课文佐证技法·匹配则引(0821)](writing-lesson-cite-unit-text-0821.md) — 不配就不引不许硬上;判据=有一篇「最突出的写法」正是本课这一招;判不引≠欠账;事实源unit-texts.md先联网核实后落笔;口径=禁指向动作不禁指代进度
- [教学指令一律正向表述(0824)](writing-lesson-positive-framing-not-prohibition.md) — 写法偏好类不判对错走三步对比,题目要求类可判;五落点(提纲表技法行/③④⑥/⑦最易漏);最大复发路径=档案自己写「避免笼统地说…」;反向刹车见源条
- [电报体/生造词红线第7条(0731/0819)](writing-lesson-telegraphese-and-coinage-redline.md) — 五形态自查(省主语/名词压缩/电报短语/生造词/中心宾语残缺);补宾语只在定义句补一次
- [学段口气全线没分级(0817)](writing-lesson-grade-tone-not-differentiated.md) — 判断分三层(用词/技法深度/思维层级);判据=降两级反问;0828复发:并列短语重难点只落实一半,拆开逐个问落点
- [「话轮骨架」层=池9+指纹第15字段(0817)](writing-turn-skeleton-layer-pool9.md) — 冷审打散措辞打散不掉同构;--focus/--against机检进checklist E组;⚠池9编号在后但属零件层
- [技法N件套须练全N件](technique-set-practice-all-parts.md) — 定稿前做「每件×是否产出过」对账;机检与checklist都抓不到
- [重建台账前先查缺指纹的篇(0819)](ledger-rebuild-drops-fingerprintless.md) — 先grep -L回写再重建,否则静默抹行
- [指纹块14字段+装置粒度门槛](writing-lesson-fingerprint-fields-revised.md) / [反同质化四项升级](writing-lesson-antihomogenization-upgrade.md) — 装置判据=当场演过一件事;⚠12字段说法已过时
- [正文标点全角+方括号提示体例](writing-lesson-fullwidth-punct-bracket.md) / [风格红线覆盖后续改写](style-redline-covers-edits.md) / [交付前通读语感扫](writing-lesson-naturalness-readthrough.md) — 生造/别扭须纯语感通读
- [写作课线三项命名/结构调整(0826)](writing-line-naming-flattened-0826.md) — 配套-X用/打包单层平铺/PPT带课次段;⚠pptx与anim.json必须同批改名否则防覆盖闸门静默失效;⚠Windows取目录名一律pathlib .name
- [标题与环节命名定稿](writing-lesson-title-naming.md) — 唯一源=title-naming.md;改体例前全skill搜一遍
- [首页无区头单表6行+两行文案体例(现行)](writing-lesson-front-page-single-table.md) — 0831两行体例推翻0828:目标行一句话说清学会写哪类文章;技法行首句固定「使用+构思工具名」且与正文一字一致;写详案或改style_front_page前必读
- [审题固化为③开头固定半环](writing-lesson-shenti-bianxi-fixed-half-step.md) / [第2节起步半环·L5–L6改判「定起点」+自由写作≥25分钟(0830)](writing-lesson-destress-onramp.md) / [修改符号自然用不重教](writing-lesson-revision-symbols-natural-use.md)
- [详案出PPTX](writing-lesson-to-pptx.md) / [docx页眉定版](writing-lesson-docx-header.md) / [竞品借鉴清单](writing-lesson-competitor-borrow-backlog.md) — 漏传--header-left/right静默回落读书会页眉;D3-D5/N1待做
- [作文批改工具(0818立项)](writing-correction-tool-0818.md) — 给加盟商不能做skill;判据从详案抽标准包JSON;错别字层原理上不能做;引用一字不差靠工程;**0907上线闸门:verified_by_human=true才打包(confirm_pack.py);线上12课,下线名单见源条**
- [批改工具已部署Vercel(0824)](writing-correction-tool-vercel-deploy-0824.md) — 入口=部署根index.py不能放api/;.vercelignore挡config.json;正式地址grader.skyline666.top;⚠validate全绿≠包对
- [配套json富文本标记只有部分字段解析(0907)](writing-materials-richtext-field-scope.md) — 教师materials/家长oneline走textContent,写{b}会印成(b);⚠溢出/页数/Type3三道机检全绿也抓不到,渲完正则扫一遍PDF文本
- [手改只改HTML必被重渲冲掉(0821)](writing-materials-handedits-lost-on-rerender.md) — 文字改动一律回写_data.json;⚠仓内9课json仍不含那批手改
- **PPT链**(六条细节→[链索引](ppt-chain-index.md)):⚠本仓止于动画注入·终稿不回仓(0902,打包不收PPT,下一课次先确认收到的是初稿)｜⚠先读详案再审查再动画(0806,机检全过≠审查完成;PPT对详案错勿迁就)
## 看图写话（picture-writing）
**排新课或出图前必读**:[总地图v5](picture-writing-course-map-v5-0728.md) · [角色口径](picture-writing-character-roster-policy.md) · [三图位两道硬门](picture-writing-three-image-slots.md) · [写规格判据](picture-writing-imgspec-writing-lessons.md) · 下方通则整块
### 跨课次通则(排同类课次直接适用 · 展开见各源条)
- **课上不安排拼贴/剪裁/涂胶**(0805推翻背靠背贴):双面卡课前印好直接发,当堂翻面承载;发卡落点紧挨用卡那步 — [源](picture-writing-2a-lesson3-state.md)
- **示范例文念两版**:先念缺新学的那版让学生自己听出缺口,第二版才添 — [源](picture-writing-2a-lesson3-state.md)｜**详案写了「人人开口」就逐环节数谁真开了口**(举手答/个别说/三人朗读不算) — [源](picture-writing-2a-lesson3-state.md)
- **表情类结果词禁令**:「露出上排牙齿」是结果词;低龄欢快靠眯眼弯月+腮红+动作,闭嘴笑最稳 — [源](picture-writing-1a-lesson2-state.md)
- **五官类返工回生成端改规格重出**,别在脚本--edit耗轮次(两次实测失效) — [源](picture-writing-1a-lesson2-state.md)
- **参考图带不住左右与地点**:辨识锚改位置式,左右不作验收项;组内同地点逐件重写标志物 — [源](picture-writing-1a-lesson3-state.md)
- **出图两判据**:同类物件常态与异常会被合并(拉距离+各给颜色);改参考图须正向逐项点名 — [源](picture-writing-2a-lesson3-state.md)
### 规则与体例
- [全64课主角角色口径(0804)](picture-writing-character-roster-policy.md) — 情境图课次必用班底+必填定妆参考;44课已全表排定照取不自拟｜[总地图v5·0728重排期(现行)](picture-writing-course-map-v5-0728.md) — 24方法课次坐标全改+四问拆两问
- [一课三图位+意外点两道选图硬门](picture-writing-three-image-slots.md) — 三图必交齐(纯口头课不豁免);四问类主图无意外点=一票否决
- [写图位规格根因级判据](picture-writing-imgspec-writing-lessons.md) / [朝向类必须写四件几何](picture-writing-orientation-must-be-geometric.md) — 约束身体朝向非脸朝向;「看着X」须写转角+瞳孔+连线+高度;已提进image-spec §A模板
- [B级链+比例唯一控制点=定妆图(0730)](picture-writing-b-level-char-ref-landed.md) — 比例只能靠改定妆图调(提示词数值/禁令实证无效勿加回);A级锚图链已摘除
- [画风靠锚图锁定](picture-writing-image-style-lock.md) / [全局两档令牌](picture-writing-global-style-tokens.md) — 现行三处令牌须一字一致;厚涂改造已终止勿重启
- [角色册已落盘assets](picture-writing-character-sheet-landed.md) — 事实源=assets/角色册/角色设定.md｜[详案输出一课次一目录(0803)](picture-writing-detail-dir-per-lesson.md) — 图位路径未变;image_dir旧布局回落分支不可删
- [详案标题三行体例](picture-writing-title-naming.md) / [提纲页行名教研通用词(两线)](outline-row-names-teaching-terms.md) — 七行新名=style_front_page PROFILES键,改md必同步脚本
- [首页定版三区提纲页](picture-writing-front-page-3zones.md) / [删四维目标节](picture-writing-opening-simplified.md) — 「（本课）」标记必留;style_front_page.py必跑
- [骨架A/B两层工作流](ability-ladder-AB-layer-workflow.md) / [索引三个坑](ability-ladder-index-reading-pitfalls.md) — B层定稿后回录只抄不设计;冲突以course-map为事实源
- [去AI味五类语言肌理](deai-language-rules-solidified.md) — 规则=lesson-structure §13;判据=读出声像不像真老师顺嘴讲｜[0804审计docx落地+立正样本](picture-writing-prose-style-benchmark-0804.md) — 意见有牙齿的才被执行;⚠二上两篇已失效勿改;⚠短句占比本线不可作筛查线
- [细节四方向→细节四问](picture-writing-sifang-renamed-siwen.md) / [两项全仓术语统一](terminology-unified-image-and-model-essay.md) — 下水文→示范文、锚图→主图
- [附录两节包注释不进docx](picture-writing-appendix-comment-wrap.md) — 生图工单/自检整区包注释;正文禁悬空转引
- [配套物料skill落地](picture-materials-skill-created.md) — 薄shim复用writing _shared.py;家长页禁虚构学生作品
## 读书会详案（lesson-plan）
**写详案前必读**：[逐环节装载量双向核查](lesson-plan-per-step-load-audit.md) · [创意环节正向标准三件套](lesson-plan-positive-standard-over-negative.md) · [环节标题三段式](lesson-plan-step-title-format.md)
- [环节标题=功能·内容三段式(0807)](lesson-plan-step-title-format.md) — 功能名≤10字、同课时内不重复;规则在style-and-format+checklist
- [一节讲不完的根因](lesson-plan-lesson-total-load-fit.md) / [创意环节防平庸=正向标准三件套](lesson-plan-positive-standard-over-negative.md) — 课堂动作量必须按标称配时倒算;只堆负向约束→模型取平庸下限
- [逐环节装载量双向核查](lesson-plan-per-step-load-audit.md) / [三类文本差异化](lesson-plan-three-text-type-focus.md) — 过挤过松都查,≥5分钟环节须有学生动作;名著优先·三选一互斥
- [详案偏薄根因=师话密度低](lesson-plan-shihua-density.md) — 三杠杆补厚(师话写长/参考填实/原文精读用足)
- [导读钩子要切题](lesson-plan-hook-must-fit-theme.md) / [预测锚点须是已读内容](lesson-plan-prediction-anchor-must-be-read.md) / [导入钩子须先声夺人](lesson-plan-intro-hook-must-grip.md) — 禁次要情节线做钩子;钩子埋了要兑现
- [导读课开场话术反同质化](lesson-plan-opening-antihomogenization.md) / [跨书查重防工具套路化](lesson-plan-cross-book-dedup.md) — 示范句禁逐字照抄、避「先不急着/先不忙」前缀家族;同一工具连用两本即换型
- [学生课前已人手一本书](students-already-have-book.md) / [教室无黑板白板](classroom-no-blackboard.md) / [详案禁ASCII图用表格](lesson-plan-no-ascii-diagram-use-table.md) — 禁假悬念;检索黑板/板书/白板应零;工具一律MD表格
- [思维工具讲解从简](lesson-plan-tool-intro-concise.md) / [师话比喻须配得上学段](lesson-plan-metaphor-age-fit.md) — 禁标「首次出现」,判据=结构绕不绕;比喻判据「给三年级讲是否一模一样」
- [SKILL通读审计A-D闭环](lesson-plan-skill-audit-fixes.md) / [阅读计划表不算可视化工具](reading-plan-not-vistool.md) — 判据数字唯一源=checklist;与rubric有意重叠不得互删
- [详案复盘冷启动化](detail-review-cold-start.md) / [复盘三文件去冗余](review-rubric-single-source-dedup.md) — 派fresh子agent冷审;review-rubric是五维/协议唯一源
- [PPT链产出后详案页标回注必做](ppt-draft-pageback-mandatory.md) / [ppt-draft参考答案上屏从宽](ppt-draft-reference-answer-generous.md) — 〖PPT第N页〗必做并重渲docx(docx常被WPS锁须先关)
## 建档（book-profile）
**给任何书建档前必读**：[全文通读红线](book-profile-full-read-redline.md) · [插图前置到建档阶段](book-profile-read-images-during-profiling.md)
- [建档必须全文通读(红线)](book-profile-full-read-redline.md) — 严禁框架/选读代替;骑鹅框架式建档实测出三硬伤
- [插图前置到建档阶段(0806)](book-profile-read-images-during-profiling.md) — 通读时逐张目视+档案加插图指针节;角色归属须锚定原文句锁不住写「未定」;三坑见源条
- [图单判读四类失败模式(0807)](illustration-judgement-failure-modes.md) — 人工核对结论不写回图单=没核;⚠页码压画面交人工别用脚本
- [可引用原文栏取成段](book-profile-quote-full-passage.md) / [类型字段禁空泛「儿童小说」](book-type-no-generic-children-fiction.md) — 下游需成段并保留原书弯引号;类型须具体文学类型
- [低段/合集建档差异](low-grade-collection-profile-formalized.md) — 区分变量是「低段」非「快乐读书吧」
## 引擎与下游物料
**碰引擎/共享件前必读**：[下游六件抽共享层](downstream-shared-layer-and-token-facts.md)（改真源照该条回归法）· [0727上下文瘦身收官](context-engineering-slimdown-0727.md)（细节已下沉references别抄回）
- [宣传件渲染链+PDF反查源三指纹(0826)](promo-materials-render-chain.md) — 手改PDF前先三指纹反查源html;馆内海报scale须0.98;海报html已改入库
- [配套PDF的Type3字体病已修两线(0817)](pdf-type3-fonts-fixed.md) — 装饰图标改纯CSS图形非换emoji;.mark .sym字体栈中间那档雅黑勿删;已装check_type3
- [外部改稿docx回贴md(0902-0907)](external-docx-backfill-0902.md) — docx_backfill.py骨架继承+文本整替;⚠判新旧看措辞不看哈希;⚠先互比外部目录历次版本定基线;⚠**清扫排版噪音的正则禁用\s,用[ 　]字符类**;示范文三方不同步以PPT+配套为基准;取舍权在用户;先读首页[授课提示]
- [下游六件抽共享层+token账实测](downstream-shared-layer-and-token-facts.md) — 合并skill省不了token;三条真源+薄壳;改真源照该条回归法(PDF比字节数不比md5)
- [0727上下文瘦身收官](context-engineering-slimdown-0727.md) / [docx引擎标题层版式](docx-engine-title-heading-layout.md) / [引擎冗余审计](docx-engine-redundancy-audit.md) — 细节已下沉references别抄回;拆三脚本已评估→不拆
- [两个常驻文件的分层重构(0818)](memory-index-structure-over-size-0818.md) — MEMORY真病灶=通则被埋进课次条目;CLAUDE下沉判据=脚本docstring才是细则唯一源;机检脚本见L2
- [读书会详案原书插图链路(0730)](lesson-plan-book-illustration-chain.md) — 详案写【图位:插-01｜图注】禁md图语法;⚠PROFILES字段CLI默认值一律None;PPT与阅读单吃图未做
- [官方skill环境事实+禁令理由(0824)](office-skills-env-facts-0824.md) / [md里HTML标签会原样印进docx](md-html-tags-leak-into-docx.md) — 新建路径跑得通、禁令只靠纪律;转PDF/PNG只有Office COM用shot_assets.py;行内强调只用成对**
- [fix_quotes会毁代码块里的命令(0807)](fix-quotes-breaks-code-blocks.md) — 不认代码围栏;含命令示例的md跑完须回扫还原半角
- [Bash heredoc写文件六坑(0820/0821)](bash-heredoc-file-writing-pitfalls.md) — 定界符漏引号反引号被执行成空;超长静默截断;替换失败先grep数次数;报错都指错方向,细节见源条
- [Write吞弯引号→必跑fix_quotes](write-tool-normalizes-curly-quotes.md) / [下游JSON引号统一弯引号禁「」](json-materials-curly-quotes.md) / [雅黑弯引号显示半角](curly-quotes-render-halfwidth-yahei.md) — 含引号段落Edit改用无引号锚点;字符层U+201C已对别改JSON,靠模板unicode-range落宋体
- [配图工具：多页道具须定妆件+示范文的「我」是大人(0903)](imgtool-prop-consistency-and-owner-0903.md) — 帆布包三错同根因;道具定妆必开去人物条目;款式写到托特/书包这一级
- **PPT引擎**:[第三profile宣讲(0824)](ppt-promo-profile-0824.md) / [按profile分层·原语不fork](ppt-profile-seam-architecture.md) / [中文变Calibri:latin须在ea前](ppt-font-ea-latin-order.md) / [表格](ppt-table-autofit.md)·[原文齐读](ppt-quote-autofit.md)自适应(存量须重烘) / [阅读单页型已下线](ppt-reading-sheet-page.md)
- **PPT 视觉**：[副标题克制电报体](ppt-subtitle-no-telegraphese.md) / [参考答案红字上屏](ppt-reference-answer-on-slide.md) / [逐条点击动画](ppt-click-reveal-animation.md) / [四图网格](ppt-four-image-grid.md) / [逐页讲稿新增docx](lecture-notes-docx.md) — 末条:打包只收docx
- **工程坑**:题目带全角＿＿则place_pptx必认领失败须手工归位;配图空占位机检查不出须肉眼看 — [源](woheguoyitian-4a-ppt-chain-state.md)
- [测评卷SKILL状态](reading-assessment-skill-state.md) / [测评事实以详案为准](assessment-facts-follow-lesson-plan.md) — 详案升深度蓝本(事实仍锁档案);与SKILL默认相反遇分叉先确认
- [阅读指南拓展栏点名具体书/影片](reading-guide-extension-concrete-titles.md) — 仅此栏放宽红线,吃不准就不写
## 未决事项与交付风险（做完即删）
- **⚠ 神笔马良 插-24 页码未裁，不得对外交付** — [详情](shenbi-maliang-lesson-plan-state.md)
- **⚠ 阅读单线 18 份 PDF 的 Type3 字体遗留未修** — [详情](pdf-type3-fonts-fixed.md)
- 彼得·潘档案 line23/32 与机读块不一致待清理 — [详情](peterpan-book-profile-state.md)｜封面图缺(汉修先生/呼兰河传/骑鹅旅行记,骑鹅须补图重跑)·快乐王子下游未做·快乐读书吧6本已建2本余4本
- **⚠四下第八单元现行习作待核实**——定了才能改63→62、序32回填、馆内海报两格重渲;总地图docx原件未换版 — [详情](gushi-xinbian-5a-unit-move-0828.md)
- 《推荐一个好地方》两处详案↔PPT微差未拍板 · writing 竞品借鉴 D3–D5/N1 待做 · ppt-profile Phase3 待办
- **⚠故事新编PPT三处待外部改+批改标准包未开工** — [详情](gushi-xinbian-5a-unit-move-0828.md)｜我来编童话PPT六类页须外部重做+Vercel未重部署 — [详情](textbook-revision-same-title-new-page-0902.md)｜漫画老师0820对方改动未合入 — [详情](manhua-laoshi-5a-lesson-state.md)
- **⚠L5-L6起步0830改判「定起点」后,余4篇五年级稿未回改**(自由写作均低于25分钟新下限;故事新编0908已回改、缩写故事已下线) — [详情](writing-lesson-destress-onramp.md)
- **⚠六上两篇下游全空**(变形记/多彩的活动:配套·标准包·PPT均未做;多彩的活动另欠冷审,排在配套前) — [详情](liushang-6a-two-lessons-state.md)
## 已交付归档
全部课次/书目状态钩子已移至[归档索引](memory-index-archived-deliveries.md),排新课次前按需打开;已落地/已验完的规则历史条目在[规则归档](memory-index-archived-rules.md)。
