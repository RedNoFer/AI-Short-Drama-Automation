# 规则传播登记表

改任何一条规则前先查本表：**权威定义只允许在「定义文件」里改**，其余文件是引用/执行点，必须同步核对；涉及默认值改动升 `policy.json` 版本号并跑 `scripts/tests/`。改完在表底登记日期。

图例：★定义文件（单一事实来源）；□执行/引用；⚙机检落点；▲反例案例。

## 规则索引

| ID | 规则 | ★定义文件 | □执行与引用点 | ⚙机检 | ▲案例 |
|---|---|---|---|---|---|
| R1 | 四段结构【参考】【公共总规范】【时间轴】【收尾】，禁【参数】；时间行自然语言（起-止秒，首镜直写、其后「硬切，」），镜头编号只存内部逐镜表 | compact-import.md | SKILL（阶段4/5）、prompt-review、validation-contract、drama-compact-package-template 注释、multi-agent-execution | validate_compact_package（HEADINGS/【参数】拦截/旧标记行拦截） | PROC-02/03 |
| R2 | 镜头行自然语言：Seedance按画面动作开场规则；Wan按R20镜头前置；两轨均禁箭头/次数缩写/代码批注 | compact-import.md（含改写对照表） | SKILL 阶段4、prompt-review、validation-contract、policy.prompt_style | validate_compact_package（opening 正则 + literal 拦截） | PROC-03 |
| R3 | 七类声音来源标签 + 「口型」+ 直引号 + 字秒比与跨切申报 | compact-import.md | SKILL 阶段4、prompt-review、validation-contract、policy.voice | validate_compact_package（标签/口型/速率） | PROC-03 |
| R4 | 声线母版（3–5 锚点、反差、旁白/混叠/低语）+ 公共层「声线锁定：」机械派生、跨片段逐字一致 | voice-and-dubbing.md ★；母版实例存内部/03 | SKILL（输入/阶段2/4/5/边界）、execution-checklist（2/4/5/触发点）、compact-import、prompt-review、asset-image-production、delivery-contract、project-brief、quality-inputs、validation-contract、模板注释、openai.yaml、multi-agent-execution | validate_compact_package（锁定存在/说话覆盖/跨片一致），policy.voice | PROC-04 |
| R5 | 上下文衔接：镜/片段/集的站位、视线、道具状态链、场景光向、情绪话头；收尾写下一片段入口 | compact-import.md（第5条） | SKILL（阶段3源稿验收、阶段4提示词编译/评审、阶段5机械集成）、prompt-review（衔接维度+空间专项）、story-evaluation、runtime-planning、multi-agent-execution | continuity_facts.py＋阶段3/4门；语义评审复核因果与表达 | SPACE-01、SYNC-01 |
| R6 | 分阶段评审：上游各自在交接点验收；阶段 4 全集提示词完成后做一轮独立全覆盖评审；阶段 5 只做机械集成检查；修复时按哈希和依赖范围定向复验 | prompt-review.md | SKILL（阶段门/1/5/速度）、execution-checklist（6）、compact-import、delivery-contract、multi-agent-execution、policy.review、story-evaluation | 无（流程闸） | PROC-02 |
| R7 | 小说原文块逐字来自用户源文件（支持 docx）；差异须授权登记；部分章节须声明范围 | compact-import.md | SKILL 阶段5、execution-checklist（阶段5）、prompt-review（上游交接）、project-brief（源文件登记）、multi-agent-execution | validate_novel_coverage.py（命中≥0.99/覆盖≥0.95） | — |
| R8 | Seedance/Wan 默认 30 秒片段、6–11 镜、5–10 硬切；Seedance 整数秒/分档 2000·3000·4500，Wan 0.5 秒/仅硬上限18000、无字数下限；H3 见 R25/R30 | runtime-planning.md；数值在 policy.video | SKILL（输入/阶段3/边界）、compact-import、prompt-review、validation-contract、delivery-contract | validate_compact_package（时间轴/硬切/字符） | PROC-02 |
| R9 | 资产版式按轨：Wan 角色图＝9:16 竖版正面单人全身塑像图（占高92%–94%）；Seedance/H3 角色资产按各自规范；场景 16:9 单张**空镜**全景（0 人 0 车 0 手持道具）；真人资产先写真实感锚；图片提示词不带声音 | asset-image-production.md；policy.assets.scene_prompt | SKILL 阶段2、compact-import、character-asset-prompts 技能 | validate_compact_package（16:9/四视图/全景字样＋场景人物/车辆/油润词/真实感锚） | — |
| R10 | 各轨包内零 @Image/@图片 编号，遵循R21b；H3用 `<Picture N>` 且未上传不得预写；绑定代码=【参考】代码；每片段至多一场景 | compact-import.md | SKILL 阶段4、prompt-review、validation-contract、model-branch-matrix | validate_compact_package（@Image 拦截、绑定/参考/场景数校验） | SYNC-01 |
| R11 | 阶段门：必读白名单、内部档案落盘、执行账一行结论，禁跳读/合并阶段/记忆引用 | execution-checklist.md | SKILL（阶段门）、multi-agent-execution（派单与放行）、project-brief | 无（流程闸） | PROC-01 |
| R12 | 多智能体隔离执行：总控/执行员/评审员分离子任务，交接包给路径不给全文，母版冻结后才能并行 | multi-agent-execution.md | execution-checklist（执行方式）、SKILL（阶段门）、policy.execution | 无（流程闸） | PROC-01 |
| R13 | 反例回收：偏差/原因/验证分栏，结论必须接入实际检查点，不固化个案参数 | failure-cases.md | SKILL（反例回收）、各阶段引用 SPACE/SYNC/PROC | 案例触发的规则进 R1–R12 机检或评审视角 | SPACE-01/SYNC-01/PROC-01..04 |
| R14 | 导入请求 ≤32 MiB；实际接口参数提交前核对 | compact-import.md；policy.delivery | delivery-contract | validate_compact_package（请求字节估算） | — |
| R15 | 改编只发生在剧本层；小说原文块逐字；抽象心理先影视化 | story-evaluation.md | runtime-planning、SKILL 阶段1、prompt-review（剧情交接） | validate_novel_coverage.py（原文侧） | — |
| R16 | 关键文字线索观众可达：无可读文字政策下由角色口述传达，道具纸面锁不可辨字 | prompt-review.md（画面执行） | compact-import、SKILL 阶段3/4 | 无（语义评审，2026-10 两轮评审形成） | 三千国道字条/湿纸条案例 |
| R17 | 阶段派单使用填空式交接包实例，总控给路径不给全文 | handoff-template.md ★ | multi-agent-execution、execution-checklist（执行方式）、SKILL 阶段门 | 无（流程闸） | PROC-01 |
| R18 | 输入单源小说固定字段必填（路径/版本/SHA-256/范围/授权改编登记），覆盖率以此为唯一基准 | project-brief.md ★ | execution-checklist（阶段0/5）、multi-agent-execution（阶段0简包）、handoff-template、validate_novel_coverage.py | validate_novel_coverage.py | — |
| R19 | 评审严重度统一口径：阻断/重要/建议三级判定标准，机检错误不得降级 | prompt-review.md（严重度节）★ | multi-agent-execution、handoff-template（评审包）、failure-cases | 无（评审口径） | PROC-02 |
| R20 | **Wan 轨镜头前置**：每时间行以 `镜头：` 起句，镜头词在前 30%；覆盖 R2 的「画面动作开场」顺序，**仅 Wan 轨**，Seedance 轨仍按 R2 | wan30-prompt-spec.md §二/§十一★；wan30-adapter-v1.0.md §4.3 | SKILL 阶段4（Wan）、prompt-review、audit_wan30_antipatterns.py | audit_wan30_antipatterns.py（镜头词位置） | WAN30-01 |
| R21 | **参考图形态按轨**：Wan3.0 用9:16竖版正面单人全身塑像图（占高92%–94%）并作为视频参考；Seedance/H3按各自分支规范。历史WAN30-07不覆盖当前Wan定义 | asset-image-production、compact-import、wan30-prompt-spec §二/§四、wan30-adapter §4.1 | asset-image-production、compact-import、SKILL阶段2/4、execution-checklist（阶段2/4） | 人工核对角色图形态、占高、正面、单人；生成后按提示词检查脸部一致性 | WAN30-07（历史案例）、WAN30-01 |
| R21b | **包内零编号**：任何轨的交付包不得写 `@ImageN`/`@图片N`；参考块只用 `代码＝职责`（代码后不重复名称），正文用姓名；编号归应用按上传槽位生成 | asset-reference-binding.md ★；compact-import.md | wan30-prompt-spec §三、wan30-adapter §4.1、model-branch-matrix、模板 | `validate_compact_package.py`（WAN30-04，各轨全局） | WAN30-04 |
| R22 | **Wan 反例硬规则**：静物≤2s、空镜≤2.5s、删极缓慢、禁三人以上人物群排、每段不看镜头、对话单镜≤6s、道具时序、文字物理规避、项目画风/实有光源、公共层与镜头层分工及语义去重（无篇幅占比门槛） | wan30-prompt-spec.md §十一★；failure-cases.md WAN30-01 | wan30-adapter §4.3/§6/§11、compact-import、prompt-review | audit_wan30_antipatterns.py＋validate_compact_package --model wan30 | WAN30-01 |
| R23 | **人物分身预防**：参考图单人、每镜≤3张正脸、4+人拆镜、五人全景≤2s且无台词、人数锁定句、普通反射不映人、幻境复刻标 `幻境层` | wan30-prompt-spec.md §十一·人物分身专项★；failure-cases.md WAN30-02 | wan30-adapter §4.3/§11/§12、asset-image-production、prompt-review、SKILL 阶段2/4 | audit_wan30_antipatterns.py（identity_overload/five_person_*/group_dialogue_overload/group_shot_budget/reflection_ambiguity） | WAN30-02 |；多人镜头的正文名单写法统一按Wan规范的五人镜头裁决执行，完整身份与位置对应保存在冻结站位合同
| R24 | **反例投喂契约**：最小信息集（提示词全文/生成参数/成片/偏差/期望/修正版/入口）、批量目录约定、五步处理（归类合并→偏差/原因/修订/验证分栏→接入检查点→回写规范并逐项核对→回执对照表）、边界（单次生成错误≠提示词缺陷、不固化个案配置、复盘不启动生成） | failure-intake-contract.md ★ | failure-cases（接收与更新）、SKILL（反例回收）、rule-map | 无（流程闸） | 全部案例类 |
| R25 | **MiniMax H3 轨**：官方结构化正文（base 三字段／Ref2VA 六段式）、片段时长沿用应用单位（官方 4–15 秒为模型单条输出上限）、毫秒切点 `At MM:SS.mmm`、首镜无时间戳、资产→`<Subject N>`/`<Picture N>`/`<Video N>`/`<Audio N>` 标签、台词 `<d>[语言]…</d>`＋`(S1)`、不写四段结构与「硬切，」行、正文硬顶 6000 字符/过简提醒 1200（官方未设字符上限，官方生产范例 2500–4540 字符；Ref2VA 的 detailed_description 按官方 350–500 词）、硬切带 0–6 | 官方原文 `25 minimax H3官方skill/skills/h3-prompt-writing/`（不改写）；本地适配 `.agents/skills/minimax-h3-adapter/SKILL.md`★；compact-import.md「MiniMax H3 轨」节；素材引用规则 `.agents/skills/minimax-h3-adapter/references/asset-reference.md`；数值 policy.model_profiles.h3 | SKILL（阶段3/4/5 三轨）、workflows.md W17、execution-checklist（阶段3/4/5）、prompt-review、project-brief、runtime-planning、story-evaluation、handoff-template、asset-image-production（参考素材前置）、voice-and-dubbing、micro-expression-layer、fight-router、validation-contract | validate_compact_package --model h3（回归 scripts/tests/test_h3_validator.py）；audit_h3_prompt.py（回归 .agents/skills/minimax-h3-adapter/scripts/tests/test_audit_h3_prompt.py） | — |
| R26 | **阶段 2 资产独立评审**：与起草方隔离的新上下文审身份锚点/角色美工账/声线母版/持物链/空间基底，不读下游；结论落盘 `内部/03b-资产评审.md`，缺记录即阶段门判错 | execution-checklist.md（执行方式 7／阶段2 落盘）★ | SKILL（阶段门/阶段2）、multi-agent-execution（派单表/纪律 9）、policy.review.stage_reviews、asset-image-production | validate_stage_artifacts（stage2 查评审记录存在且 ≥60 字符） | CHARACTER-01、PROC-04 |
| R27 | **视感自查可机检**：每片段一段「视感统计：」六键行＋含景别/焦段/机位/运镜四列的逐镜表；声明值与实算值逐项比对，固定占比/连续固定/连三近景/焦段与机位种数按实算判定 | storyboard-selfcheck.md ★；数值 policy.storyboard_selfcheck | SKILL（阶段3）、execution-checklist（阶段3/执行方式3）、prompt-review（评审不重复手算）、policy.gates | crosscheck_storyboard.py（阶段3 门强制调用；--emit 反算）＋ scripts/tests/test_crosscheck_storyboard.py | PROC-02、DIALOGUE-01（同类：口径不可验证） |
| R28 | **阶段 3.5 打斗路由有门**：逐片段 A/B/C 必须落盘；A 级须带拍点表、一镜到底标记与原文证据；全剧无打斗写「均为 C」声明；A 级豁免镜数带与硬切的出口必须有人守 | fight-router.md ★；policy.gates.stage35_artifact | SKILL（阶段3/3.5）、execution-checklist（阶段3.5）、multi-agent-execution（派单表） | validate_stage_artifacts --stage 3.5（缺表/等级不可识别/A 级缺件均判错） | PROC-05（同类：可豁免硬规却无门） |
| R29 | **门查结构不查关键字**：必登标题下必须有正文、表格必须有数据行、每角色在美工账各一行、持物链须有箭头链或表格行；空壳文档骗门与跳步同级 | execution-checklist.md（执行方式 3）★ | SKILL（阶段门）、multi-agent-execution（纪律 8） | validate_stage_artifacts（_require_section／_table_rows／角色行比对） | PROC-05、审计 2026-10-23 |
| R30 | **一条主线＋三种模型 profile**：阶段 0 登记 `seedance25`/`wan30`/`h3` 单轨；阶段 0–3.5 剧情/资产/合同/空间/分镜共用，只拆阶段 3 片段形态、3.5 A 级、4 编译器/评审附录、5 校验器；不得混写三轨模板；Seedance 2.0（S02/S07/S13）是独立路由族，不是 30 秒多镜主线的 seedance25 profile | workflow-spec.md ★；model-branch-matrix.md ★；policy.workflow | SKILL（输入/阶段3/4/5）、execution-checklist（分支与固定落盘名）、prompt-review（分支附录）、compact-import、fight-router、project-brief、handoff-template、runtime-planning | `validate_workflow_manifest.py --strict`（生成轨/01c/05/06/执行账/唯一包；回归 scripts/tests/test_workflow_manifest.py） | 2026-10-23 分支审计 |
| R31 | **提示词分层与去重**：一个事实只写一处；资产图写全外观/空间/形制，不写镜头/台词/表演/剧情动作/第二套服装；视频只写机位/走位/动作/状态变化，不重写资产图已锁的脸、服装剪裁材质、建筑结构材质、道具尺寸纹样；三锚只写发型／固定饰件／外套品类＋固有色 | prompt-layering.md ★ | SKILL 阶段2/4、execution-checklist、asset-image-production、asset-reference-binding、prompt-review、wan30-prompt-spec、wan30-adapter、compact-import、outfit-variants | `validate_compact_package.py`（资产镜头/台词词、三锚面料剪裁词、视频硬亮线、场景空镜人物/裸车；场景/道具细节簇提醒）；`validate_stage_artifacts.py --stage 2`（03b 分层段提醒） | LAYER-01、WAN30-04、SCENE-01 |
| R32 | **参考图绑定与数量**：只绑定本段画内角色；建议总数 2–6 张，Wan3.0 硬上限 10 张；7–10 张允许，须在【参考】中逐项写清本段职责，不得为满足建议值删掉有效参考；同型角色不并挂，先靠硬锚拉距 | failure-cases.md WAN30-08★；wan30-prompt-spec.md §二/§四 | prompt-review（⑥硬规）、execution-checklist（阶段4）、wan30-adapter §4.1 | validate_compact_package（绑定角色超出画内人数提醒；>6 提示复核职责；>10 阻断） | WAN30-08 |
| R33 | **角色一致性全包同源**：同一角色的锚词在全包逐字一致；禁止「遵循 CHAR_0X 参考图」这类无锚简版；改一处必须全量回灌 | failure-cases.md WAN30-09★、WAN30-06 | prompt-review（⑦分层与去重）、execution-checklist（阶段4）、SKILL 阶段4 | validate_compact_package（WAN30-09 提醒：同角色跨段锚词不一致） | WAN30-09 |
| R34 | **Wan服装分层**：9:16全身人物资产图锁定默认全套服装（含下装、鞋）；视频正文只写发型／固定饰件／外套品类＋固有色三锚，不重复下装与鞋；状态变化写「在参考图基础上」，真换装走服装变体 PROP | failure-cases.md OUTFIT-03★、outfit-variants.md | 阶段2资产完整性、prompt-review（⑦）、execution-checklist（阶段4） | validate_compact_package（WAN30-04 禁止视频三锚重复裤鞋） | OUTFIT-03（历史案例）、OUTFIT-01/02 |
| R35 | **文字物理规避**：画面可能出现可读文字（车牌、路牌、招牌、门牌、包装、屏幕）时，镜头行必须给物理手段（糊泥/雨水、避角、浅景深、前景遮挡、被身体挡住）；只写禁止项不算落实 | failure-cases.md TEXT-02★、TEXT-01 | prompt-review（⑥硬规）、wan30-prompt-spec §十一、execution-checklist（阶段4） | audit_wan30_antipatterns（legible_text_closeup_risk）＋抽帧核对 | TEXT-02、TEXT-01 |
| R36 | **阶段3分镜完整覆盖阶段1计划**：逐镜片段 ID 与 `02a-结构化拍摄剧本.json` 的 episode/segment 清单一一对应；缺段、重复、计划外或只提交部分片段均阻断 | workflow-spec.md ★；阶段1/分镜映射在故事档案与 `02a` | SKILL（阶段3）、execution-checklist、multi-agent-execution、执行账 | `validate_stage_artifacts.py --stage 3`＋`test_stage_gates.py` | PROC-07 |
| R37 | **字数与校验器失败关闭**：提示词长度只取项目登记轨的 profile；Wan 长度策略缺字段时不得回退 Seedance；`--tier` 仅限 Seedance；旧式 `validate_delivery.py` 拒绝 Wan/H3/未登记模型 | policy.json 分支 profile、model-branch-matrix.md ★ | AGENTS、SKILL、validation-contract、multi-agent-execution、failure-cases | `validate_compact_package.py`、`validate_delivery.py`＋分支回归测试 | PROC-07 |
| R38 | **剧情保留与敏感内容表达**：固定事件/责任/结果/线索；用含蓄且可执行的画面保留观众接收依据；跨语言与参考检查、锁定台词不默改；改变冻结展示先同步受影响上游；输入/输出报错与实际验证分开，不保证审核 | content-expression.md ★ | SKILL（阶段3/4）、prompt-review、execution-checklist、handoff-template；build_handoff 阶段3及三轨阶段4必读 | 无关键词黑名单；生成派单卡检查必读路径与R38；语义由既有阶段3/4独立评审 | CONTENT-01 |
| R39 | **画面文字纪律（公共层统一，禁任何字幕）**：Wan3.0 含台词或心声的片段，【公共总规范】必须有一行以 `画面文字纪律：` 开头的统一句（逐字取自 wan30-adapter 4.2 第 5 块；全帧无字幕/双语/翻译/标题/时间码/角标/水印，对白以声音＋口型、画外与听筒段同样无字幕）；不得只写禁止项否定 token，不得并进禁止项清单或逐镜改写 | wan30-adapter-v1.0 §4.2/§8 ★、wan30-prompt-spec 模块二/注释、compact-import 阶段4 | prompt-review、execution-checklist（阶段4）、SKILL 阶段4 | 阶段4独立评审必查＋样片抽帧核对；机检 `画面文字纪律：` 行存在性待回填补 | TEXT-03 |

## 文件职责速查（改文件时先判断它是不是定义文件）

- `SKILL.md`：流程总纲，只写阶段顺序与原则，规则细节链接到定义文件；避免在此复制规则全文（复制=未来漂移点）。
- `policy.json`：全部机器可读默认值；改默认值升版本号。
- `references/*`：R1–R31 的定义与执行细则。
- `scripts/`：确定性检查；新硬规则先问能否机检，能就进脚本并补 `scripts/tests/` 正反用例。
- `assets/drama-compact-package-template.md`：导入端结构模板，注释只写格式不写项目值。
- `agents/openai.yaml`：入口默认提示词，只做引导，不承载规则。

## 变更登记

| 2026-10-20 | R24 | 新增反例投喂契约，批量反例接收标准化（后续新案例归入 R24 流程） | failure-intake-contract、failure-cases、SKILL、rule-map |

| 日期 | 规则 | 变更 | 同步的文件 |
|---|---|---|---|
| 2026-10-23 | R31 | 新增提示词分层与去重：资产图只写外观/空间/形制，视频只写机位/动作/状态变化；三锚收窄为发型／固定饰件／外套品类＋固有色；机检新增资产镜头/台词词、三锚面料剪裁词、视频硬亮线，场景/道具细节簇提醒；四个交付包同步收窄三锚（policy v24） | prompt-layering.md（新）、SKILL、execution-checklist、asset-image-production、asset-reference-binding、prompt-review、wan30-prompt-spec、wan30-adapter、compact-import、outfit-variants、failure-cases、policy.json、validate_compact_package.py、validate_stage_artifacts.py |
| 2026-10-23 | R30、R6/R8/R10/R25 | 新增「一条主线＋三种模型 profile」；统一 H3 app 30 秒默认、official 4–15；修正评审六视角、参考语法与字符/时长口径 | workflow-spec.md、model-branch-matrix.md、SKILL、execution-checklist、prompt-review、compact-import、fight-router、project-brief、handoff-template、policy、workflows.md、router |
| 2026-10-23 | R31 补强 | 场景图空镜机检补裸「车」：正向句出现「车」判错，车道/车站/车位/车库/车辙/车流/车行与否定句除外；补 3 条回归；四个包同步去车/去材质复述 | policy.json、validate_compact_package.py、test_scene_plate.py、prompt-layering.md、rule-map |
| 2026-10-18 | R1–R4、R6–R8 | 四段结构、自然语言、声线体系、覆盖率、评审回滚建立 | 见 SKILL 与 PROC-02..04 |
| 2026-10-19 | R6 | 两轮评审 → 一次对抗性独立评审 + 修复复验（policy v7） | SKILL、prompt-review、checklist、compact-import、PROC-02 |
| 2026-10-19 | R12 | 新增多智能体隔离执行；本表建立（policy v8） | SKILL、checklist、multi-agent-execution、rule-map、openai.yaml |
| 2026-10-19 | R1 时间行 | 镜头 ID 与竖线标记移出提交正文，切镜改自然语言；校验器与 8 个自测用例同步 | 全 skill+交付包 |
| 2026-10-19 | R17–R19 | 交接包实例模板、输入单源文件强制字段、评审严重度口径（流程文档增补，机检规则不变，policy 维持 v8） | handoff-template、project-brief、prompt-review、rule-map、checklist |
| 2026-10-20 | R20–R22 | Wan3.0 首轮样片反例回写：镜头前置、视频参考图类型、静物/空镜/并肩/不看镜头/对话时长/道具时序/文字规避/冷灰光；新增反例审计脚本与 policy.anti_patterns | wan30-prompt-spec、wan30-adapter、failure-cases、policy.json、rule-map、audit_wan30_antipatterns.py |
| 2026-10-20 | R23 | 人物分身反例回写：参考图单人、每镜≤3张正脸、4+人拆镜、五人全景≤2s无台词、人数锁定句、反射标幻境层；审计新增身份预算检查 | failure-cases WAN30-02、wan30-prompt-spec、wan30-adapter、policy.json、audit_wan30_antipatterns.py、rule-map |
| 2026-10-23 | R26–R29 | 防错前移（审计缺口）：阶段 2 加资产独立评审并进阶段门；视感自查改为可机检表＋新增 `crosscheck_storyboard.py`（声明值 vs 实算值）；阶段 3.5 打斗路由新增出口门；门从关键字检查升级为结构检查（空标题/空表格/账上缺行均判错）；角色九块字段提醒前移到阶段 2（policy v23） | SKILL、execution-checklist、multi-agent-execution、storyboard-selfcheck.md（新）、prompt-review、asset-image-production、policy.json、validate_stage_artifacts.py、crosscheck_storyboard.py（新）、tests/test_stage_gates.py、tests/test_crosscheck_storyboard.py（新） |
| 2026-10-23 | R21 修订、R23 补强、R32–R35 新增 | 三千国道二轮成片反例：同一段内阿泽 9s/13s 两张脸（脸占画面 1/8、85mm 近景无脸可依）→ 视频参考改场景内剧照、身份板退回存档；46/52 段挂全员参考→加参考图预算；6 段简版一致性→加全包同源；服装只锁外套→加服装锚三项；车牌可读→加文字物理规避 | failure-cases（WAN30-07/08/09、OUTFIT-03、TEXT-02、WAN30-03 修订、WAN30-02 补强）、prompt-review、asset-image-production、execution-checklist、rule-map、validate_compact_package.py |

| 2026-10-25 | R8/R9/R21、R30、Wan目标字符 | 清除跨轨字数/参考图冲突；Wan3.0固定16:9正面单人全身塑像（当日口径；晚些改为 9:16 竖版，见下条 R9 画幅定版）、当时提示词长度口径（已由2026-10-26 policy v32取消目标带/下限并改为18000硬顶）；校验器从输入单推断唯一轨、拒绝错轨与Seedance档位串用；阶段4门运行本轨校验器和Wan审计；并行批次加输入/输出SHA-256锁与隔离草稿；policy v25 | AGENTS.md、policy.json、asset-image-production、compact-import、wan30-prompt-spec、prompt-review、failure-cases、rule-map、execution-checklist、handoff-template、multi-agent-execution、validate_compact_package.py、validate_stage_artifacts.py、tests/test_compact_validator.py、项目输入单与执行账 |
| 2026-10-25 | PROC-07 防回归 | 分支矩阵去除 Seedance 的无条件默认轨表述；明确未登记/无效/重复时失败关闭、用户指定分支优先、字符目标只取所选 profile；修正 Wan 资产参考图残留的 9:16 规格；补测 Wan 单人塑像图不触发通用四视图 gate | model-branch-matrix.md、workflow-spec.md、scripts/tests/test_compact_validator.py |
| 2026-10-25 | R36 / PROC-07 补强 | 阶段3门新增与阶段1冻结分段计划对账，缺段/重复/计划外阻断；校验器 API 缺模型轨时失败关闭，Wan 角色资产必须声明塑像形态 | validate_stage_artifacts.py、validate_compact_package.py、SKILL.md、execution-checklist.md、test_stage_gates.py、test_compact_validator.py |
| 2026-10-25 | R37 / PROC-07 补强 | Wan 字数策略缺项时拒绝回退 Seedance 3000；`--tier` 限 Seedance；旧式图像文件校验器明确并强制 Seedance 2.5 轨；为字数 profile 缺失与旧校验器错轨添加回归测试 | AGENTS.md、SKILL.md、validation-contract.md、validate_compact_package.py、validate_delivery.py、test_compact_validator.py、test_validate_delivery_branch.py |
| 2026-10-25 | R9 画幅定版（用户裁决） | **Wan3.0 角色资产图改为 9:16 竖版单人全身塑像图**，成片视频仍按登记画幅（默认 16:9）；资产画幅与视频画幅解耦，互不推导，同项目禁横竖混用；policy 升 v27（`assets.wan30_character_ratio`＝9:16），机检按该字段判错；竖版收益依赖编码器吃图方式，center-crop 会切头脚，首次出图须看预览缩略图 | asset-image-production.md、policy.json、AGENTS.md、wan30-prompt-spec.md、wan30-adapter-v1.0.md、model-branch-matrix.md、compact-import.md、outfit-variants.md、failure-cases.md、handoff-template.md、validation-contract.md、tests/test_compact_validator.py |
| 2026-10-26 | R8/R22、Wan内容验收 | 用户明确取消Wan总长度下限、目标带、单拍字数配额与章节篇幅占比门槛，仅保留18000字符硬上限；逐镜按剧情、动作因果、构图/运镜/焦点、情绪表演、光影环境、声音口型、出口衔接验收；旧卡按规范快照重发，不凭取消下限自动放行旧稿；policy v32；回归19个文件348项通过，Skill结构校验通过 | policy.json、Wan规范/适配器、SKILL、导入/评审/交接/分支矩阵、workflow_common、包校验器、Wan审计、派单与lint回归测试 |
| 2026-10-26 | Wan分支复核，policy v33 | 清除固定五人参考、另一套拍点数量、固定阴天光源等旧模板要求；取消按动作词数判密度的启发式，反应镜按剧情/可见表演审查；路由显式指向Wan，Seedance档限定其分支；补测反应镜与导入自定义标题拒绝；19个现行测试文件350项通过，主Skill与路由Skill结构校验通过 | Wan规范/适配器、router、policy、audit_wan30_antipatterns、tests |

| 2026-10-26 | policy v34：规则边界闭合 | Wan统一四段、取消动作数量配额、镜头前置与光源继承不再互相冲突；warning以当前指纹和独立证据处置，硬错不可豁免；阶段3连续性事实先验收并冻结、阶段4正文交叉验；中文与泰语估时分开，原语估时依据归声线规范。只修受影响产物及接口，不重跑无关已通过内容 | SKILL、分支矩阵、Wan规范/适配器、workflow-spec、execution-checklist、multi-agent-execution、prompt-review、policy、相关既有脚本 |
| 2026-10-27 | R38 新增 | 将保留剧情事实的敏感内容表现适配接入分镜/提示词编写、同轮语义评审与自动派单；区分原语台词保留风险和输入/输出审核，不将候选词写成通用禁词。未改模型默认值、未增加关键词机检或评审轮次 | content-expression.md（新）、SKILL、prompt-review、execution-checklist、handoff-template、failure-cases、build_handoff.py、test_build_handoff.py |
