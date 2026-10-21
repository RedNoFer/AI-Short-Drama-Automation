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
| R6 | 评审机制：一次对抗性独立评审（五视角、带证据），回滚后全量复验；独立子任务、记录模板、4 次预算、升级用户 | prompt-review.md | SKILL（阶段门/1/5/速度）、execution-checklist（6）、compact-import、delivery-contract、multi-agent-execution、policy.review、story-evaluation | 无（流程闸） | PROC-02 |
| R7 | 小说原文块逐字来自用户源文件（支持 docx）；差异须授权登记；部分章节须声明范围 | compact-import.md | SKILL 阶段5、execution-checklist（阶段5）、prompt-review（上游交接）、project-brief（源文件登记）、multi-agent-execution | validate_novel_coverage.py（命中≥0.99/覆盖≥0.95） | — |
| R8 | 30 秒片段、6–8 镜、5–7 硬切、整数秒连续时间轴、正文≤2000 字符 | runtime-planning.md；数值在 policy.video | SKILL（输入/阶段3/边界）、compact-import、prompt-review、validation-contract、delivery-contract | validate_compact_package（时间轴/硬切/字符） | PROC-02 |
| R9 | 资产版式：角色 16:9 白底四视图、场景 16:9 单张全景；图片提示词不带声音 | asset-image-production.md；policy.assets | SKILL 阶段2、compact-import、character-asset-prompts 技能 | validate_compact_package（16:9/四视图/全景字样） | — |
| R10 | 不预写 @Image/@图片 编号；绑定代码=【参考】代码；每片段至多一场景 | compact-import.md | SKILL 阶段4、prompt-review、validation-contract | validate_compact_package（@Image 拦截、绑定/参考/场景数校验） | SYNC-01 |
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
| R21 | **视频参考图类型**：角色视频参考只用单张、场景内、3/4 侧身、同套剧情服化、方向光、可见皮肤纹理、无文字的电影剧照；白底四视图只做图片资产与设定存档 | wan30-prompt-spec.md §二/§四★ | asset-image-production、compact-import、SKILL 阶段2/4、wan30-adapter §4.1 | 人工验收清单（图片内容无法机检）；交付包记录参考图类型 | WAN30-01 |
| R22 | **Wan 反例硬规则**：静物≤2s、空镜≤2.5s、删极缓慢、禁三人以上人物群排、每段不看镜头、对话单镜≤6s、道具时序、文字物理规避、冷灰光、公共总规范≤20% | wan30-prompt-spec.md §十一★；failure-cases.md WAN30-01 | wan30-adapter §4.3/§6/§11、compact-import、prompt-review | audit_wan30_antipatterns.py＋validate_compact_package --model wan30 | WAN30-01 |
| R23 | **人物分身预防**：参考图单人、每镜≤3张正脸、4+人拆镜、五人全景≤2s且无台词、人数锁定句、普通反射不映人、幻境复刻标 `幻境层` | wan30-prompt-spec.md §十一·人物分身专项★；failure-cases.md WAN30-02 | wan30-adapter §4.3/§11/§12、asset-image-production、prompt-review、SKILL 阶段2/4 | audit_wan30_antipatterns.py（identity_overload/five_person_*/group_dialogue_overload/group_shot_budget/reflection_ambiguity） | WAN30-02 |
| R24 | **反例投喂契约**：最小信息集（提示词全文/生成参数/成片/偏差/期望/修正版/入口）、批量目录约定、五步处理（归类合并→偏差/原因/修订/验证分栏→接入检查点→回写规范并逐项核对→回执对照表）、边界（单次生成错误≠提示词缺陷、不固化个案配置、复盘不启动生成） | failure-intake-contract.md ★ | failure-cases（接收与更新）、SKILL（反例回收）、rule-map | 无（流程闸） | 全部案例类 |

## 文件职责速查（改文件时先判断它是不是定义文件）

- `SKILL.md`：流程总纲，只写阶段顺序与原则，规则细节链接到定义文件；避免在此复制规则全文（复制=未来漂移点）。
- `policy.json`：全部机器可读默认值；改默认值升版本号。
- `references/*`：R1–R23 的定义与执行细则。
- `scripts/`：确定性检查；新硬规则先问能否机检，能就进脚本并补 `scripts/tests/` 正反用例。
- `assets/drama-compact-package-template.md`：导入端结构模板，注释只写格式不写项目值。
- `agents/openai.yaml`：入口默认提示词，只做引导，不承载规则。

## 变更登记

| 2026-10-20 | R24 | 新增反例投喂契约，批量反例接收标准化（后续新案例归入 R24 流程） | failure-intake-contract、failure-cases、SKILL、rule-map |

| 日期 | 规则 | 变更 | 同步的文件 |
|---|---|---|---|
| 2026-10-18 | R1–R4、R6–R8 | 四段结构、自然语言、声线体系、覆盖率、评审回滚建立 | 见 SKILL 与 PROC-02..04 |
| 2026-10-19 | R6 | 两轮评审 → 一次对抗性独立评审 + 修复复验（policy v7） | SKILL、prompt-review、checklist、compact-import、PROC-02 |
| 2026-10-19 | R12 | 新增多智能体隔离执行；本表建立（policy v8） | SKILL、checklist、multi-agent-execution、rule-map、openai.yaml |
| 2026-10-19 | R1 时间行 | 镜头 ID 与竖线标记移出提交正文，切镜改自然语言；校验器与 8 个自测用例同步 | 全 skill+交付包 |
| 2026-10-19 | R17–R19 | 交接包实例模板、输入单源文件强制字段、评审严重度口径（流程文档增补，机检规则不变，policy 维持 v8） | handoff-template、project-brief、prompt-review、rule-map、checklist |
| 2026-10-20 | R20–R22 | Wan3.0 首轮样片反例回写：镜头前置、视频参考图类型、静物/空镜/并肩/不看镜头/对话时长/道具时序/文字规避/冷灰光；新增反例审计脚本与 policy.anti_patterns | wan30-prompt-spec、wan30-adapter、failure-cases、policy.json、rule-map、audit_wan30_antipatterns.py |
| 2026-10-20 | R23 | 人物分身反例回写：参考图单人、每镜≤3张正脸、4+人拆镜、五人全景≤2s无台词、人数锁定句、反射标幻境层；审计新增身份预算检查 | failure-cases WAN30-02、wan30-prompt-spec、wan30-adapter、policy.json、audit_wan30_antipatterns.py、rule-map |
