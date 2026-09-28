# Project Memory: laojohn-lesson-plan
> **索引维护规则(0818立·0901补)**:①新增课次/单本书状态→进[归档索引](memory-index-archived-deliveries.md),不占索引行;②横向通则→各线「跨课次通则」块,不埋进课次条目;③未决/交付风险→「未决事项」块,做完即删;④优先级集中在各区头行;⑤行数≤150、单条钩子≤200字符、细节下沉主题文件,超限先归档,机检挂SessionStart hook自动跑;⑥CLAUDE.md只写现行规则,来历/日期/旧口径进记忆;压缩前快照=[0923](memory-index-archive-20260923.md)
## 用户偏好
- 中文回复;简洁直接不堆客套;重要决策先列选项让用户拍板;视觉迭代常用截图反馈
- **问「有没有做到X」时是要判断、不是指出问题**——先自己核查给结论,别把判断权反问回去
## 跨技能硬约束（三条详案线通用）
**动笔写任何详案前必读**：[约束分层](constraint-layering-generation-vs-coldreview-0804.md) · [机构课场景](venue-is-institution-not-school.md) · [真实情境官方锚点](real-situation-official-anchor-first.md)
- [约束分层:措辞层后移到冷审PassB(0804)](constraint-layering-generation-vs-coldreview-0804.md) — 判据=修这处要不要动教学设计;生成只读简报+正样本;冷审PassA结构/PassB行文各派fresh agent;⚠改规则文件勿破tone_gate四解析锚｜[首次实测四项全过](layering-first-measurement-0804.md)
- [机构课·没有课本没有校内作息](venue-is-institution-not-school.md) — 「校内同步」只指跟教材进度不指地点;禁「翻开课本/晨读/课间」,教材图一律投屏;与[教室无黑板](classroom-no-blackboard.md)同族
- [真实情境先查官方锚点·兑现必须课内闭环](real-situation-official-anchor-first.md) — 别自造载体(标「已自含」的尤其);没有「下次课读上次稿」;承诺全班读到就得兑现
- [评价机制禁靠学生自报弱点(0803)](no-self-report-mechanisms.md) — 「我是蒙的」没人会说,判定开关空转;改客观结果自证｜[合集新亚型:有班底无情节主线(0807)](collection-with-cast-no-plotline.md) — 「人物贯穿≠情节贯穿」+封死全书级工具;多出「辑内」层｜[0726审查三项拍板](skills-audit-fixes-0726.md) — 改AI腔检核/两线checklist前必读
- [⚠改已定稿详案三坑(0915)](revise-finalized-lesson-plan-pitfalls-0915.md) — PPT改页清单左栏=pptx现状非详案旧状(误读会撤回有效批评);新写师话先grep下游`参考：`行防剧透;重跑docx第一步会冲掉style_front_page;三样都静默、机检抓不到
## 架构速览（骨架事实 · 细节在各 SKILL）
- 主链与平行分支见 CLAUDE.md §2｜每课时双产出中间稿+讲稿页序1:1;页号唯一口径=中间稿P号==讲稿##第N页==详案页标〖PPT第N页〗;PPT不标页码角标;中间稿不写师话(师话→讲稿);眉标禁写课型
- **双人协作(0820)**:口径见 CLAUDE.md §9;记忆事实源=仓内 .claude/memory/,用户目录那份是目录联接;看板与commit前缀0911已取消 — [详情](two-person-sync-0820.md)
- **skill停用归档0910立·0911撤回**:只省description 2.8k字符(窗口0.2%),误触发方向反;22个全部在架,别再重做;活线两处查找与gitignore skills*通配保留无害 — [详情](skills-parked-0910.md)
- **⚠「版权材料仅限内部备课·不得转发」已删(0924用户拍板)**:本仓+`_assets`全部素材可对外用、可进图生视频;16处一次改齐;别再以此拒绝 — [详情](copyright-forwarding-restriction-removed-0924.md)
- **家长短视频宣传片线(0924只出方案未写代码)**:9:16成片·运镜+图生视频+_assets课堂照片·豆包TTS+老师声音克隆;复用lesson-video底层走薄壳 — [详情](promo-video-line-plan-0924.md)
## 写作课（writing-lesson）
**写任何一篇前必读**:[0911换靶](generation-retarget-0911.md) · [文风定盘](writing-style-two-directions-conflict-0831.md) · [例子四判据](writing-lesson-example-must-be-unique-anchor.md) · [比喻反刻板](writing-lesson-metaphor-antistereotype.md) · [电报体红线](writing-lesson-telegraphese-and-coinage-redline.md) · [示范文「我」同龄](model-essay-persona-student-age-0914.md) · [跨课次通则子索引](memory-index-writing-lesson-rules.md) 整块
### 跨课次通则 → 已外移 [写作课跨课次通则子索引](memory-index-writing-lesson-rules.md)（0919，排新课次前整块打开；新通则加进那里、不回本文件）
### 规则与体例
- [⚠规则效力评估0915:素材层做到了·咬合三条零落地](model-essay-rules-effect-eval-0915.md) — 四篇同尺盲评;0912够得着需与0914叠加才判得出丙;C2旁批表双标准四篇全未达标;根因=checklist把三条压进同一个勾;要领数上限缺「补进核心技法行」出口;机检②③④全绿≠合格
- [示范文规则0912补五条+机检E+瘦身](model-essay-rules-supplement-0912.md) — 够得着上限=优等学生;旁批表最见功夫两句必入表;不教第四招;起笔不与③反例同型;§六第7问;essay_audit.py每份必跑;⚠已拆条文+history,生成只读顶部一屏卡,别把来历写回条文
- [⚠用张视角审详案的四口径+三条不采纳(0918)](zhang-perspective-audit-checks-0918.md) — 先取数(师话朗读时长/逐环节占比/伪问题逐条/材料套数);⚠**他的处方默认是「删」而仓内内容被档案与规则锁**,正确动作＝保内容减讲法;别把「设计好的缺口」当伪问题删掉
- [张祖庆视角接入写作课线(0912)](zhang-zuqing-on-writing-line-0912.md) — 三处落位:生成侧generation-brief§一.8减法三问/冷审rubric跨维九+维三三问/示范文链;体系审计8条已拍板采5不采3(讲评按需·审题依需·三档表);话语比不能当判据;三档优先级标记不推广
- [⚠0911换靶:生成侧语体=规范教案·瘦身41%来历下沉·polish_writing机械层·PassB四个不执行机制](generation-retarget-0911.md) — 生成只读简报§一.7+prose-exemplars;避让卡替代整读pools/ledger;A/B待做
- [⚠文风定盘0831·0901收敛一主三从](writing-style-two-directions-conflict-0831.md) — 方向=向规范书面靠;AI痕迹=破折号/导演腔/省主语/术语漂移;**PassC已撤别重开**;主判据唯一源style-criteria+执行位在PassB;改写工序跑完必看--baseline方向指标;批量修文件脚本每步立即写盘;⚠方言词表已实测否掉勿加回
- [教师自拟例子四条硬判据(0817)](writing-lesson-example-must-be-unique-anchor.md) — 独一份/夸张≠计数/样板不低于例句/一篇内锚点不复用;管全篇例子不只示范文
- [比喻类写人反刻板+示范材料不绑老师真实生活(0802/0817)](writing-lesson-metaphor-antistereotype.md) — 「先想只有他家才有的画面再找动物」做成课堂明线;例子不落老师家人;默认措辞不强断言老师当下生活事实
- [⚠2026秋第三例换题·一次五处(0914)](textbook-2026-five-retitles-0914.md) — 四上六/七八互换/五上七/六上七八;事实源七文件+宣传件四份+存量三份详案已全改齐;全新题archive零命中不得动笔;迁册降级须重标;宣传件四份全过期未改(样课举例印着已删题)
- [⚠动笔前按最新版教材核单元课文(0914)](textbook-latest-edition-verify-first-0914.md) — 六上2026秋换版;篇目/题目先查仓内textbook-2026梳理PDF,要素与题面靠用户实物页;⚠标「已逐字核对」的旧实拍记录同样会过期(五上四0915照出四处错·已进师话);四上六/七/八·五上七·六上七/八习作换题course-map待拍板
- [③引本单元课文佐证技法·匹配则引(0821)](writing-lesson-cite-unit-text-0821.md) — 不配就不引不许硬上;判据=有一篇「最突出的写法」正是本课这一招;判不引≠欠账;事实源unit-texts.md先联网核实后落笔;口径=禁指向动作不禁指代进度
- [教学指令一律正向表述(0824)](writing-lesson-positive-framing-not-prohibition.md) — 写法偏好类不判对错走三步对比,题目要求类可判;五落点(提纲表技法行/③④⑥/⑦最易漏);最大复发路径=档案自己写「避免笼统地说…」;反向刹车见源条
- **承接学生发言要复述他说的具体内容再往下讲(0918)**:只写「是的/对」＝空承接;判据＝遮住`参考：`行师话还读得通就是没接住;四形态(单一答案直接确认/分散答案复述再归类/有分歧点出两边/多人各说一例压成短语或结论前置);⚠复述别照抄学生口语(「念」在方向指标口语词表)、别写成预演式 — [源](prose-exemplars-echo-student-answer-0918.md)
- [电报体/生造词红线第7条·十形态(0731→0921)](writing-lesson-telegraphese-and-coinage-redline.md) — ⚠**0921把六～十形态补进规则文件四处+tone_gate候选清单**(此前只在记忆里,三篇连着复发);⑥偏僻动词扩散⑦宣告式任务句⑧「X好了，就…」⑨动宾自造⑩隐喻化动词(立起/长成/挂到中心上/写得最厚)与术语半截化(说明方法说全名);判据改问「单独读给没上过这课的人,知道说的是什么、落在哪吗」;⚠`参考：`保留口语粗糙不保生造搭配;打磨完必复跑tone_gate
- [学段口气全线没分级(0817)](writing-lesson-grade-tone-not-differentiated.md) — 判断分三层(用词/技法深度/思维层级);判据=降两级反问;0828复发:并列短语重难点只落实一半,拆开逐个问落点
- [技法N件套须练全N件](technique-set-practice-all-parts.md) — 定稿前做「每件×是否产出过」对账;机检与checklist都抓不到｜⚠**同族第二病:自拟材料要按「步」拆开核要素是否齐全**(四上五正例中间一步无听觉、师话却把落在第一步的嗡嗡声算进去,通读查不到——整体读起来三样都有,漏的是「都在同一步里」) — [源](shenghuo-wanhuatong-4a-lesson-state.md)
- [首页无区头单表6行+两行文案体例(现行)](writing-lesson-front-page-single-table.md) — 0831两行体例推翻0828:目标行一句话说清学会写哪类文章;技法行首句固定「使用+构思工具名」且与正文一字一致;写详案或改style_front_page前必读
- [三档标准改学生可见(0921)](three-tier-standard-student-visible-0921.md) — 〔…教师掌握（不必读给学生）〕括注以后都不写;lesson-structure+checklist已改;tone_gate无需改;存量45份不回溯
- [作文批改工具(0818立项)](writing-correction-tool-0818.md) — 给加盟商不做skill;判据从详案抽标准包JSON;主模型doubao-2-1-pro(必带thinking=disabled);闸门verified_by_human;0921经真稿实测已改到第七版栏目与判据(⚠「立得住」不禁·成语误用排第一·修辞改法禁另造喻体·起手式靠程序轮换角度治不住提示词);⚠改提示词必跑run_regression
- [批改工具已部署Vercel(0824)](writing-correction-tool-vercel-deploy-0824.md) — 入口=部署根index.py不能放api/;.vercelignore挡config.json;正式地址grader.skyline666.top;⚠validate全绿≠包对
- [⚠配套三侧文风0915与详案线同步换靶](writing-materials-retarget-0915.md) — 生成读三侧定稿样本不读对照表;polish_materials.py机检D每份必跑(同一张polish_rules,禁副本);存量42份已过一轮;样本卡=现行json快照,--check-exemplars防漂移(抄样本抄现行文件别抄git diff);⚠配套--all --dry-run是共享规则表第二回归面,首跑照出4条排除漏洞
- ⚠**改配套共享模板一律「加可选字段、不动默认值」(0916–0922)**:45份共用`template_student.html`;已有 plan_name(工具名须与教师口头一致)／plan_hint(填表分钟数)／plan_label_width(首列宽);改它必跑零影响回归(判据=重渲存量,PDF页数与逐页文本逐字相等);⚠logo 0921换1200px致PDF涨137KB不是改坏,42份旧PDF待重渲;⚠**PPT稿纸页=学生用第2页截图**,配套一改即过期(直出件用grab_worksheet.py现截,不过期) — [详情](materials-template-optional-fields-0922.md)·[源](manhua-laoshi-5a-lesson-state.md)
- [⚠写作课单元海报工具(0920立项)](writing-poster-tool-0920.md) — 独立skill;7份已出余17份未跑;**出图前先立意推敲**:AI给2-3方向(带立意·画风·元素数·风险)→用户拍板→才写subject,留痕_brief;⚠比喻题禁画喻体实体;⚠立意过关≠方向过关(多场景天然碎);**排新海报前整份打开**
- [配套json富文本标记只有部分字段解析(0907)](writing-materials-richtext-field-scope.md) — 教师materials/家长oneline走textContent,写{b}会印成(b);⚠溢出/页数/Type3三道机检全绿也抓不到,渲完正则扫一遍PDF文本
- [手改只改HTML必被重渲冲掉(0821)](writing-materials-handedits-lost-on-rerender.md) — 文字改动一律回写_data.json;⚠仓内9课json仍不含那批手改
- **PPT链**(八条细节→[链索引](ppt-chain-index.md)):⚠外部件:本仓止于动画注入·嵌图终稿不回仓(0902,打包不收PPT,下一课次先确认收到的是初稿);直出件是终稿、入库并push｜⚠先读详案再审查再动画(0806,机检全过≠审查完成;PPT对详案错勿迁就)｜⚠[表头重影层每次顺手清·删在注入前(0915)](ppt-header-ghost-image-0915.md)｜⚠[动画禁由下向上(0915)](ppt-anim-no-upward-jump-0915.md) — 撤销0804「哪怕跳回顶部」;表格按行揭示;页脚条载任务指令须上移先出;交付前必跑回跳校验
## 看图写话（picture-writing）
整区（跨课次通则＋规则体例）已外移 → **[看图写话线记忆](memory-index-picture-writing.md)**，排新课次或出图前打开；该线当前无未决项。
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
- [⚠一轮冷审后的多轮局部改稿必须二次冷审(0918)](local-edits-need-second-cold-review-0918.md) — 6/10项A块伤是改稿自己引入的(含真实性与机构课两条红线);固定查三类＝可数断言重测/回指逐处验/术语表对全文;一轮绿灯不继承;两轮意见相反时找第三条路不选边
- [详案复盘冷启动化](detail-review-cold-start.md) / [复盘三文件去冗余](review-rubric-single-source-dedup.md) — 派fresh子agent冷审;review-rubric是五维/协议唯一源｜[冷审报告可删·台账分层0915](cold-review-report-retention-0915.md) — 三件齐即删报告;判读表≤250字符/行,明细进detail档;阈值8按31点定案维持(外部生成稿不适用)
- [PPT链产出后详案页标回注必做](ppt-draft-pageback-mandatory.md) / [ppt-draft参考答案上屏从宽](ppt-draft-reference-answer-generous.md) — 〖PPT第N页〗必做并重渲docx(docx常被WPS锁须先关)
## 建档（book-profile）
**给任何书建档前必读**：[全文通读红线](book-profile-full-read-redline.md) · [插图前置到建档阶段](book-profile-read-images-during-profiling.md)
- [建档必须全文通读(红线)](book-profile-full-read-redline.md) — 严禁框架/选读代替;骑鹅框架式建档实测出三硬伤
- [插图前置到建档阶段(0806)](book-profile-read-images-during-profiling.md) — 通读时逐张目视+档案加插图指针节;角色归属须锚定原文句锁不住写「未定」;三坑见源条
- [图单判读四类失败模式(0807)](illustration-judgement-failure-modes.md) — 人工核对结论不写回图单=没核;⚠页码压画面交人工别用脚本
- [可引用原文栏取成段](book-profile-quote-full-passage.md) / [类型字段禁空泛「儿童小说」](book-type-no-generic-children-fiction.md) — 下游需成段并保留原书弯引号;类型须具体文学类型
- [低段/合集建档差异](low-grade-collection-profile-formalized.md) — 区分变量是「低段」非「快乐读书吧」
## 引擎与下游物料
- [直出PPT完成即入库并push(0926)](direct-ppt-commit-and-push-0926.md) — 给同事在GitHub上看;长期授权不必再问;直出用图不入库;打包收直出件PPT(认文档属性标记)
- **写作课PPT仓内直出(0926)**:六上五终稿v12(新规则重排,0926晚)存仓外共享盘(不在桌面);0927按第11条出v13(桌面,换10页活动图);以后重写详案的课次走直出(direct_build.py+每课构建脚本);外部件添图收尾用finalize_external.py;六上五终稿用外部配图版v9(加稿纸页、删讲评,在桌面),其详案页标未同步待定;母版dc.html+自建html_to_pptx.py替代Design导出;六上五试点v2在桌面;主题色胶囊+吉祥物+手指图标已定为默认(写进母版增补);讲评环节一律不进课件PPT;认可后才改CLAUDE.md§3/外部链记忆 — [详情](writing-ppt-direct-build-pilot-0926.md)
- [claude.ai 旧 skill 快照已删净(0920)](skill-snapshots-cloud-cleared-0920.md) — 三份 06 月快照连同 daily-post/picture-book-recommend 用户手动删除(有意);重名冲突根除,CLAUDE.md §5 警告块已压缩;⚠误用自查点(产物落 写作课输出\ 或文件名缺-第N单元-)日后再传 skill 仍管用
**碰引擎/共享件前必读**：[下游六件抽共享层](downstream-shared-layer-and-token-facts.md)（改真源照该条回归法）· [0727上下文瘦身收官](context-engineering-slimdown-0727.md)（细节已下沉references别抄回）
- [手绘风格库274条全改九项+按用途标签(0924)](handdraw-library-retune-0924.md) — style_tags.json封闭词表(媒介/年龄感/题材/基调/色彩/人物造型+写作课招生档);读书会/绘本按书气质组合筛;特征只写画风不写内容;gpt-image照抄参考图服装改特征治不了
- [课件配图工具接手绘风格库+缺省gpt-image(0924)](imgtool-handdraw-gptimage-0924.md) — 解析抽成与海报共用的handdraw_style.py;风格卡`手绘编号`走compose();通道钉project.通道、老项目按已有图目录认(七个全gemini);⚠规则库在gpt-image上未重验
- [宣传件渲染链+PDF反查源三指纹(0826)](promo-materials-render-chain.md) — 手改PDF前先三指纹反查源html;馆内海报scale须0.98;海报html已改入库
- [配套PDF的Type3字体病已修两线(0817)](pdf-type3-fonts-fixed.md) — 装饰图标改纯CSS图形非换emoji;.mark .sym字体栈中间那档雅黑勿删;已装check_type3
- [外部改稿docx回贴md(0902-0915)](external-docx-backfill-0902.md) — 骨架继承+文本整替;⚠判新旧看措辞不看哈希;⚠先互比外部历次版本(同晚两份或是平行方案须问采哪份);⚠外部统一术语会并掉配套上两样东西;⚠清扫噪音正则禁\s用[ 　];三方不同步以PPT+配套为基准;取舍权在用户;先读首页[授课提示]
- [下游六件抽共享层+token账实测](downstream-shared-layer-and-token-facts.md) — 合并skill省不了token;三条真源+薄壳;改真源照该条回归法(PDF比字节数不比md5)
- [两个常驻文件的分层重构(0818)](memory-index-structure-over-size-0818.md) — MEMORY真病灶=通则被埋进课次条目;CLAUDE下沉判据=脚本docstring才是细则唯一源;机检脚本见L2
- [读书会详案原书插图链路(0730)](lesson-plan-book-illustration-chain.md) — 详案写【图位:插-01｜图注】禁md图语法;⚠PROFILES字段CLI默认值一律None;PPT与阅读单吃图未做
- [官方skill环境事实+禁令理由(0824)](office-skills-env-facts-0824.md) / [md里HTML标签会原样印进docx](md-html-tags-leak-into-docx.md) — 新建路径跑得通、禁令只靠纪律;转PDF/PNG只有Office COM用shot_assets.py;行内强调只用成对**
- [fix_quotes会毁代码块里的命令(0807)](fix-quotes-breaks-code-blocks.md) — 不认代码围栏;含命令示例的md跑完须回扫还原半角
- [Bash heredoc写文件六坑(0820/0821)](bash-heredoc-file-writing-pitfalls.md) — 定界符漏引号反引号被执行成空;超长静默截断;替换失败先grep数次数;报错都指错方向,细节见源条
- [Write吞弯引号→必跑fix_quotes](write-tool-normalizes-curly-quotes.md) / [下游JSON引号统一弯引号禁「」](json-materials-curly-quotes.md) / [雅黑弯引号显示半角](curly-quotes-render-halfwidth-yahei.md) — 含引号段落Edit改用无引号锚点;字符层U+201C已对别改JSON,靠模板unicode-range落宋体
- [配图工具：多页道具须定妆件+示范文的「我」是大人(0903)](imgtool-prop-consistency-and-owner-0903.md) — 帆布包三错同根因;道具定妆必开去人物条目;款式写到托特/书包这一级
- **PPT引擎**:[第三profile宣讲(0824)](ppt-promo-profile-0824.md) / [按profile分层·原语不fork](ppt-profile-seam-architecture.md) / [中文变Calibri:latin须在ea前](ppt-font-ea-latin-order.md) / [表格](ppt-table-autofit.md)·[原文齐读](ppt-quote-autofit.md)自适应(存量须重烘) / [阅读单页型已下线](ppt-reading-sheet-page.md)
- ⚠[课件添图风格样板(0925)](ppt-illustration-style-reference-0925.md) — 用户否了「原版式找空地塞小图」;要的是外部人工添图那套:每课吉祥物立页题条右端+主图占版面9–20%常出血+正文压左60%配底带;表格/稿纸/分节页不放；⚠0927 选图「画内容不画活动」(母版§四之二第11条)
- **PPT 视觉**：[副标题克制电报体](ppt-subtitle-no-telegraphese.md) / [参考答案红字上屏](ppt-reference-answer-on-slide.md) / [逐条点击动画](ppt-click-reveal-animation.md) / [四图网格](ppt-four-image-grid.md) / [逐页讲稿新增docx](lecture-notes-docx.md) — 末条:打包只收docx
- **工程坑**:题目带全角＿＿则place_pptx必认领失败须手工归位;配图空占位机检查不出须肉眼看 — [源](woheguoyitian-4a-ppt-chain-state.md)
- ⚠[改外部pptx三个静默坑(0916)](pptx-text-edit-three-silent-traps-0916.md) — 重复shape id／timing空容器／endParaRPr不在段末;三者python-pptx全读得出、PowerPoint一律拒开且不说是哪条;工具已固化`laojohn-ppt/tools/pptx_text_edit.py`;⚠0925:normalize_paragraphs遇多pPr段落反把文件改坏,只在append过run时调
- **备课视频线 laojohn-lesson-video(0921立)**:详案+PPT+教师用配套→15–25分钟备课视频,给加盟商老师自学(填师训空位);旁白＝备课解说不是照念师话,增量在教师用json三色旁注;逐句合成消掉字幕漂移;起手式靠程序轮换;⚠AiHubMix的TTS够跑管线不够交付(英文音色念中文) — [详情](lesson-video-line-0921.md)
- **⚠仓内pptx不一定是终稿(0921用户纠正)**:拿仓内那份与详案页标对账,17课次13个对不上(五上二从P7起整齐差1页)——曾据此误判「详案页标错了」。**真相：页标对的是外部终稿,仓内可能是更早版本,对不上是预期、禁批量改详案**;按页消费PPT一律用终稿 — [详情](pagemap-json-page-offset-0921.md)
- [测评卷SKILL状态](reading-assessment-skill-state.md) / [测评事实以详案为准](assessment-facts-follow-lesson-plan.md) — 详案升深度蓝本(事实仍锁档案);与SKILL默认相反遇分叉先确认
- [阅读指南拓展栏点名具体书/影片](reading-guide-extension-concrete-titles.md) — 仅此栏放宽红线,吃不准就不写
## 未决事项与交付风险（做完即删）
- **备课视频首批两支已出片(0921)**:五上四 17.8分钟为准片(外部终稿画面、增量39%、机检FAIL0、字幕零违规、零漂移);三上一 16.4分钟素材薄;六上四等PPT定稿;张视角二审三条已落地(bridge废除/locate与do重合/空泛点题词表);⚠闸门A记的是「用户指示直接出片(未逐页通读)」 — [详情](lesson-video-line-0921.md)
- **仓库瘦身已完成(0920)**：759.67→303.41 MiB（两机一致）。**⏰ 唯一待办：2026-10-04 后删远端 `backup/pre-filter-20260920`**（删前 GitHub 网页体积数字不降，属正常；删后两台机器的负向 refspec 即可撤）；⚠ 新克隆必跑两条装机命令(core.hooksPath + 负向 refspec，见 docs\协作同步说明.md)，否则大文件闸门失效、一条 git pull 就把仓库撑回 635MiB — [详情](repo-slimming-plan-0920.md)
- 三上五我们眼中的缤纷世界 0919 定稿、0922 两轮 50 处、**0923 五轮 70 余处**（**两条横向新规**：技法要当堂划适用边界〔变化三词只管当场看得完的〕＋并列多感官动词各归各位;**红线11扩第六项**＝带序数/方位/指示的回指仍要补中心词,⚠0922 我按第7条⑤判「不补」是判错;判断题的问法须在事实上站得住;⚠**提示层交代过≠学生话轮交代过**〔教具段写了的学习单,师话里一次没交代〕;⚠示范文改一个词必联动旁批表引句/示范卡/⑤两问,否则 essay_audit③ 判断链断）;机检全绿、docx 已重渲+style_front_page;PPT链0923已跑(5处PPT↔详案差异0924用户定不改)、配套三侧0923已出、批改标准包未做;**0928「学习单」全改「阅读单」＋口头化残留清理**（⚠学生用页头大标题按用户定不动·45份共用模板·未推广全仓）;短片不随教案分发（版权）；0926本仓添图配图版v5已出(整页重排)(桌面,#105同海报) — [详情](binfen-shijie-3a-lesson-state.md)
- 四上五生活万花筒 0922 两轮意见改稿定稿（一轮去 AI 腔 30 余条；二轮四处：材料衔接补过渡＋结尾改回与反例同句、示范文第二段换用户文本、「十一分钟≠一节课」、结尾讲解整段换）；**新立两条横向规则**：红线11第五项「量的类比两头须真的相当」、model-essay AI 味五查→六查（收束句无铺垫与反应失真）；0922 又压了提纲表核心技法行（99→85 字）、**配套三侧已出**（教师侧溢出须先按 15 行旁注封顶；与存量做过 10-gram 重合扫描，照出 6 处复用样本卡句已改写）、**单元海报 0922 已出**（#258 万花筒半身近景）；本仓添图配图版v5 0927按第11条换10页活动图(桌面)；PPT 链/批改标准包未做 — [详情](shenghuo-wanhuatong-4a-lesson-state.md)
- 开场「不在场第三人」另2课待回改(用户定本次只改五上四):四上一推荐一个好地方L27-31「一位朋友带孩子来玩」+老师替他读心(改它须重找判据载体,非换几句话)、三下六L44敲门送伞的孩子 — [详情](opening-no-offstage-third-party.md)
- 六上三让生活更美好：workflow③「三分型」实例仍写两把尺未改（详案已按一把尺落定） — [详情](shenghuo-meihao-6a-lesson-state.md)
- 示范文「我」视角普查余项 0924 用户定忽略、不回改（确证越界2课+存疑1课+标注未进引块1课照旧） — [源](model-essay-persona-student-age-0914.md)
- 写作线 0913 通读审计第四档（多处完整判据去重、technique-levels/SKILL/rubric 九来历下沉）未做，等两三篇新稿后再清 — [清单](writing-line-audit-0913-remaining.md)
- **⚠ 神笔马良 插-24 页码未裁，不得对外交付** — [详情](shenbi-maliang-lesson-plan-state.md)
- **⚠ 阅读单线 18 份 PDF 的 Type3 字体遗留未修** — [详情](pdf-type3-fonts-fixed.md)
- 彼得·潘档案 line23/32 与机读块不一致待清理 — [详情](peterpan-book-profile-state.md)｜封面图缺(汉修先生/呼兰河传/骑鹅旅行记,骑鹅须补图重跑)·快乐王子下游未做·快乐读书吧6本已建2本余4本
- **⚠三处「单元被搬空」待核实**:四下八、五下七、六下五(课程表与馆内海报均已标「待定」占位,63总数不变);两道全新题《我最喜爱的季节》《传承好家风》archive零命中、文体暂判,待教材页;总地图docx原件仍是换新前口径 — [详情](textbook-2026-five-retitles-0914.md)
- 《推荐一个好地方》两处详案↔PPT微差未拍板 · writing 竞品借鉴 D3–D5/N1 待做 · ppt-profile Phase3 待办
- 五上三故事新编批改标准包未开工(PPT/docx回贴0917已收官,见归档索引)｜我来编童话PPT六类页须外部重做+Vercel未重部署 — [详情](textbook-revision-same-title-new-page-0902.md)｜漫画老师0820对方改动未合入 — [详情](manhua-laoshi-5a-lesson-state.md)
- **⚠L5-L6起步0830改判「定起点」后,余1篇五年级稿未回改**(自由写作低于25分钟新下限;故事新编0908·二十年后0915·心爱之物0916·漫画老师0916已回改,缩写故事已下线) — [详情](writing-lesson-destress-onramp.md)｜0924用户定暂缓
- 五年级存量按现行写作线回改(0915起·「存量不回溯」的例外):五上一/二/三/四已完成(见归档索引「五年级回改批」),**余五下八未回改**(0924用户定暂缓)
- **六上四篇下游**：六上一 PPT链+配套三侧已出；六上二配套三侧已出·PPT未做；六上三 PPT链0916+配套0917已出；六上四 0924 外部改词新版已入库（能开、旧词清零；⚠页序变、详案页标P26起差1页、anim.json过期，用户定不回注 — [源](bijian-liuchu-6a-lesson-state.md)）；三篇批改标准包未做；四篇⑥⑦避让串已下沉 variation-pools（0915 机检已拦）
## 已交付归档
全部课次/书目状态钩子已移至[归档索引](memory-index-archived-deliveries.md),排新课次前按需打开;已落地/已验完的规则历史条目在[规则归档](memory-index-archived-rules.md)。
