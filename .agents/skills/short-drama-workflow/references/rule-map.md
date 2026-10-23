# 规则传播登记表

改任何一条规则前先查本表：**权威定义只允许在「定义文件」里改**，其余文件是引用/执行点，必须同步核对；涉及默认值改动升 `policy.json` 版本号并跑 `scripts/tests/`。改完在表底登记日期。

图例：★定义文件（单一事实来源）；□执行/引用；⚙机检落点；▲反例案例。

## 规则索引

| ID | 规则 | ★定义文件 | □执行与引用点 | ⚙机检 | ▲案例 |
|---|---|---|---|---|---|
| R1 | 四段结构【参考】【公共总规范】【时间轴】【收尾】，禁【参数】；时间行自然语言（起-止秒，首镜直写、其后「硬切，」），镜头编号只存内部逐镜表 | compact-import.md | SKILL（阶段4/5）、prompt-review、validation-contract、drama-compact-package-template 注释、multi-agent-execution | validate_compact_package（HEADINGS/【参数】拦截/旧标记行拦截） | PROC-02/03 |
| R2 | 镜头行自然语言：画面动作开场，禁焦段数字/固定机位/景别参数开场/→/×N/代码批注 | compact-import.md（含改写对照表） | SKILL 阶段4、prompt-review、validation-contract、policy.prompt_style | validate_compact_package（opening 正则 + literal 拦截） | PROC-03 |
| R3 | 七类声音来源标签 + 「口型」+ 直引号 + 字秒比与跨切申报 | compact-import.md | SKILL 阶段4、prompt-review、validation-contract、policy.voice | validate_compact_package（标签/口型/速率） | PROC-03 |
| R4 | 声线母版（3–5 锚点、反差、旁白/混叠/低语）+ 公共层「声线锁定：」机械派生、跨片段逐字一致 | voice-and-dubbing.md ★；母版实例存内部/03 | SKILL（输入/阶段2/4/5/边界）、execution-checklist（2/4/5/触发点）、compact-import、prompt-review、asset-image-production、delivery-contract、project-brief、quality-inputs、validation-contract、模板注释、openai.yaml、multi-agent-execution | validate_compact_package（锁定存在/说话覆盖/跨片一致），policy.voice | PROC-04 |
| R5 | 上下文衔接：镜/片段/集的站位、视线、道具状态链、场景光向、情绪话头；收尾写下一片段入口 | compact-import.md（第5条） | SKILL（阶段3/4/5、阶段门）、prompt-review（衔接维度+空间专项）、story-evaluation、runtime-planning、multi-agent-execution | 无（语义评审） | SPACE-01、SYNC-01 |
| R6 | 评审机制：一次对抗性独立评审（六视角＋登记轨分支硬规附录、带证据），回滚后全量复验；独立子任务、记录模板、修复复验预算、升级用户 | prompt-review.md | SKILL（阶段门/1/5/速度）、execution-checklist（6）、compact-import、delivery-contract、multi-agent-execution、policy.review、story-evaluation | 无（流程闸） | PROC-02 |
| R7 | 小说原文块逐字来自用户源文件（支持 docx）；差异须授权登记；部分章节须声明范围 | compact-import.md | SKILL 阶段5、execution-checklist（阶段5）、prompt-review（上游交接）、project-brief（源文件登记）、multi-agent-execution | validate_novel_coverage.py（命中≥0.99/覆盖≥0.95） | — |
| R8 | Seedance/Wan 默认 30 秒片段、6–11 镜、5–10 硬切；Seedance 整数秒/分档 2000·3000·4500，Wan 0.5 秒/20000；H3 见 R25/R30 | runtime-planning.md；数值在 policy.video | SKILL（输入/阶段3/边界）、compact-import、prompt-review、validation-contract、delivery-contract | validate_compact_package（时间轴/硬切/字符） | PROC-02 |
| R9 | 资产版式：角色 16:9 白底四视图、场景 16:9 单张全景；图片提示词不带声音 | asset-image-production.md；policy.assets | SKILL 阶段2、compact-import、character-asset-prompts 技能 | validate_compact_package（16:9/四视图/全景字样） | — |
| R10 | Seedance/H3 单 MD 不预写 @Image/@图片 编号；Wan 可写 `@ImageN` 但须指向真实资产；H3 用 `<Picture N>` 且未上传不得预写；绑定代码=【参考】代码；每片段至多一场景 | compact-import.md | SKILL 阶段4、prompt-review、validation-contract、model-branch-matrix | validate_compact_package（@Image 拦截、绑定/参考/场景数校验） | SYNC-01 |
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
| R21 | **视频参考图类型**：Wan3.0 角色视频参考只用 16:9 单人全身塑像图（单张、单身体、全身入画、正面、双眼平视镜头、占高 92%–94%、中性浅灰底、无文字、无场景陈设），同图锁身份与服装；四视图/多视图拼版不进视频参考。Seedance 2.5／H3 仍用四视图资产板＋单张场景剧照 | wan30-prompt-spec.md §二/§四★ | asset-image-production、compact-import、SKILL 阶段2/4、wan30-adapter §4.1 | 人工验收清单（图片内容无法机检）；交付包记录参考图类型 | WAN30-01 |
| R21b | **包内零编号**：任何轨的交付包不得写 `@ImageN`/`@图片N`；参考块只用 `代码 名称＝职责`，正文用姓名；编号归应用按上传槽位生成 | asset-reference-binding.md ★；compact-import.md | wan30-prompt-spec §三、wan30-adapter §4.1、model-branch-matrix、模板 | `validate_compact_package.py`（WAN30-04，各轨全局） | WAN30-04 |
| R22 | **Wan 反例硬规则**：静物≤2s、空镜≤2.5s、删极缓慢、禁三人以上人物群排、每段不看镜头、对话单镜≤6s、道具时序、文字物理规避、冷灰光、公共总规范≤20% | wan30-prompt-spec.md §十一★；failure-cases.md WAN30-01 | wan30-adapter §4.3/§6/§11、compact-import、prompt-review | audit_wan30_antipatterns.py＋validate_compact_package --model wan30 | WAN30-01 |
| R23 | **人物分身预防**：参考图单人、每镜≤3张正脸、4+人拆镜、五人全景≤2s且无台词、人数锁定句、普通反射不映人、幻境复刻标 `幻境层` | wan30-prompt-spec.md §十一·人物分身专项★；failure-cases.md WAN30-02 | wan30-adapter §4.3/§11/§12、asset-image-production、prompt-review、SKILL 阶段2/4 | audit_wan30_antipatterns.py（identity_overload/five_person_*/group_dialogue_overload/group_shot_budget/reflection_ambiguity） | WAN30-02 |
| R24 | **反例投喂契约**：最小信息集（提示词全文/生成参数/成片/偏差/期望/修正版/入口）、批量目录约定、五步处理（归类合并→偏差/原因/修订/验证分栏→接入检查点→回写规范并逐项核对→回执对照表）、边界（单次生成错误≠提示词缺陷、不固化个案配置、复盘不启动生成） | failure-intake-contract.md ★ | failure-cases（接收与更新）、SKILL（反例回收）、rule-map | 无（流程闸） | 全部案例类 |
| R25 | **MiniMax H3 轨**：官方结构化正文（base 三字段／Ref2VA 六段式）、片段时长沿用应用单位（官方 4–15 秒为模型单条输出上限）、毫秒切点 `At MM:SS.mmm`、首镜无时间戳、资产→`<Subject N>`/`<Picture N>`/`<Video N>`/`<Audio N>` 标签、台词 `<d>[语言]…</d>`＋`(S1)`、不写四段结构与「硬切，」行、正文硬顶 6000 字符/过简提醒 1200（官方未设字符上限，官方生产范例 2500–4540 字符；Ref2VA 的 detailed_description 按官方 350–500 词）、硬切带 0–6 | 官方原文 `25 minimax H3官方skill/skills/h3-prompt-writing/`（不改写）；本地适配 `.agents/skills/minimax-h3-adapter/SKILL.md`★；compact-import.md「MiniMax H3 轨」节；素材引用规则 `.agents/skills/minimax-h3-adapter/references/asset-reference.md`；数值 policy.model_profiles.h3 | SKILL（阶段3/4/5 三轨）、workflows.md W17、execution-checklist（阶段3/4/5）、prompt-review、project-brief、runtime-planning、story-evaluation、handoff-template、asset-image-production（参考素材前置）、voice-and-dubbing、micro-expression-layer、fight-router、validation-contract | validate_compact_package --model h3（回归 scripts/tests/test_h3_validator.py）；audit_h3_prompt.py（回归 .agents/skills/minimax-h3-adapter/scripts/tests/test_audit_h3_prompt.py） | — |
| R26 | **阶段 2 资产独立评审**：与起草方隔离的新上下文审身份锚点/角色美工账/声线母版/持物链/空间基底，不读下游；结论落盘 `内部/03b-资产评审.md`，缺记录即阶段门判错 | execution-checklist.md（执行方式 7／阶段2 落盘）★ | SKILL（阶段门/阶段2）、multi-agent-execution（派单表/纪律 9）、policy.review.stage_reviews、asset-image-production | validate_stage_artifacts（stage2 查评审记录存在且 ≥60 字符） | CHARACTER-01、PROC-04 |
| R27 | **视感自查可机检**：每片段一段「视感统计：」六键行＋含景别/焦段/机位/运镜四列的逐镜表；声明值与实算值逐项比对，固定占比/连续固定/连三近景/焦段与机位种数按实算判定 | storyboard-selfcheck.md ★；数值 policy.storyboard_selfcheck | SKILL（阶段3）、execution-checklist（阶段3/执行方式3）、prompt-review（评审不重复手算）、policy.gates | crosscheck_storyboard.py（阶段3 门强制调用；--emit 反算）＋ scripts/tests/test_crosscheck_storyboard.py | PROC-02、DIALOGUE-01（同类：口径不可验证） |
| R28 | **阶段 3.5 打斗路由有门**：逐片段 A/B/C 必须落盘；A 级须带拍点表、一镜到底标记与原文证据；全剧无打斗写「均为 C」声明；A 级豁免镜数带与硬切的出口必须有人守 | fight-router.md ★；policy.gates.stage35_artifact | SKILL（阶段3/3.5）、execution-checklist（阶段3.5）、multi-agent-execution（派单表） | validate_stage_artifacts --stage 3.5（缺表/等级不可识别/A 级缺件均判错） | PROC-05（同类：可豁免硬规却无门） |
| R29 | **门查结构不查关键字**：必登标题下必须有正文、表格必须有数据行、每角色在美工账各一行、持物链须有箭头链或表格行；空壳文档骗门与跳步同级 | execution-checklist.md（执行方式 3）★ | SKILL（阶段门）、multi-agent-execution（纪律 8） | validate_stage_artifacts（_require_section／_table_rows／角色行比对） | PROC-05、审计 2026-10-23 |
| R30 | **一条主线＋三种模型 profile**：阶段 0 登记 `seedance25`/`wan30`/`h3` 单轨；阶段 0–3.5 剧情/资产/合同/空间/分镜共用，只拆阶段 3 片段形态、3.5 A 级、4 编译器/评审附录、5 校验器；不得混写三轨模板；Seedance 2.0（S02/S07/S13）是独立路由族，不是 30 秒多镜主线的 seedance25 profile | workflow-spec.md ★；model-branch-matrix.md ★；policy.workflow | SKILL（输入/阶段3/4/5）、execution-checklist（分支与固定落盘名）、prompt-review（分支附录）、compact-import、fight-router、project-brief、handoff-template、runtime-planning | `validate_workflow_manifest.py --strict`（生成轨/01c/05/06/执行账/唯一包；回归 scripts/tests/test_workflow_manifest.py） | 2026-10-23 分支审计 |

## 文件职责速查（改文件时先判断它是不是定义文件）

- `SKILL.md`：流程总纲，只写阶段顺序与原则，规则细节链接到定义文件；避免在此复制规则全文（复制=未来漂移点）。
- `policy.json`：全部机器可读默认值；改默认值升版本号。
- `references/*`：R1–R30 的定义与执行细则。
- `scripts/`：确定性检查；新硬规则先问能否机检，能就进脚本并补 `scripts/tests/` 正反用例。
- `assets/drama-compact-package-template.md`：导入端结构模板，注释只写格式不写项目值。
- `agents/openai.yaml`：入口默认提示词，只做引导，不承载规则。

## 变更登记

| 2026-10-20 | R24 | 新增反例投喂契约，批量反例接收标准化（后续新案例归入 R24 流程） | failure-intake-contract、failure-cases、SKILL、rule-map |

| 日期 | 规则 | 变更 | 同步的文件 |
|---|---|---|---|
| 2026-10-23 | R30、R6/R8/R10/R25 | 新增「一条主线＋三种模型 profile」；统一 H3 app 30 秒默认、official 4–15；修正评审六视角、参考语法与字符/时长口径 | workflow-spec.md、model-branch-matrix.md、SKILL、execution-checklist、prompt-review、compact-import、fight-router、project-brief、handoff-template、policy、workflows.md、router |
| 2026-10-18 | R1–R4、R6–R8 | 四段结构、自然语言、声线体系、覆盖率、评审回滚建立 | 见 SKILL 与 PROC-02..04 |
| 2026-10-19 | R6 | 两轮评审 → 一次对抗性独立评审 + 修复复验（policy v7） | SKILL、prompt-review、checklist、compact-import、PROC-02 |
| 2026-10-19 | R12 | 新增多智能体隔离执行；本表建立（policy v8） | SKILL、checklist、multi-agent-execution、rule-map、openai.yaml |
| 2026-10-19 | R1 时间行 | 镜头 ID 与竖线标记移出提交正文，切镜改自然语言；校验器与 8 个自测用例同步 | 全 skill+交付包 |
| 2026-10-19 | R17–R19 | 交接包实例模板、输入单源文件强制字段、评审严重度口径（流程文档增补，机检规则不变，policy 维持 v8） | handoff-template、project-brief、prompt-review、rule-map、checklist |
| 2026-10-20 | R20–R22 | Wan3.0 首轮样片反例回写：镜头前置、视频参考图类型、静物/空镜/并肩/不看镜头/对话时长/道具时序/文字规避/冷灰光；新增反例审计脚本与 policy.anti_patterns | wan30-prompt-spec、wan30-adapter、failure-cases、policy.json、rule-map、audit_wan30_antipatterns.py |
| 2026-10-20 | R23 | 人物分身反例回写：参考图单人、每镜≤3张正脸、4+人拆镜、五人全景≤2s无台词、人数锁定句、反射标幻境层；审计新增身份预算检查 | failure-cases WAN30-02、wan30-prompt-spec、wan30-adapter、policy.json、audit_wan30_antipatterns.py、rule-map |
| 2026-10-23 | R26–R29 | 防错前移（审计缺口）：阶段 2 加资产独立评审并进阶段门；视感自查改为可机检表＋新增 `crosscheck_storyboard.py`（声明值 vs 实算值）；阶段 3.5 打斗路由新增出口门；门从关键字检查升级为结构检查（空标题/空表格/账上缺行均判错）；角色九块字段提醒前移到阶段 2（policy v23） | SKILL、execution-checklist、multi-agent-execution、storyboard-selfcheck.md（新）、prompt-review、asset-image-production、policy.json、validate_stage_artifacts.py、crosscheck_storyboard.py（新）、tests/test_stage_gates.py、tests/test_crosscheck_storyboard.py（新） |
