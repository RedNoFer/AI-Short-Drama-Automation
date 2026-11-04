# Skill: 快速生产流水线（Wan3.0 快速档）

一句话：单人单会话、单遍直出、两个检查点（一条命令机检＋一轮合评），把完全体影视工作流的包制作时间从小时级压到 35–50 分钟/章，写作质量靠完全体的规范文件保证。

**与完全体的关系**：[short-drama-workflow](../short-drama-workflow/SKILL.md) 保持不动，继续服务多人协作、全量审计与升级回退。本 skill **不复制、不修改任何写作规范**——所有"怎么写"的知识直接引用完全体 reference（引用覆盖对照表见下）；快速档只改变流程编排与检查密度。轨固定 **Wan3.0**，Seedance/H3 需要时再扩展。

## 输入

小说原文（txt/md）＋目标画风；可选：续作（复用既有固定资产卡与绑定，C 阶段降到 ≤3 分钟）。用户只给小说与画风即可，不预问集数、资产与场景决策——按完全体同样的自主规划原则从原文推导。

## 红线（六件不能省的事）

1. **参考图形态**：Wan3.0 角色视频参考＝9:16 竖版单人全身塑像图、四视图不进视频参考（[参考图类型](../short-drama-workflow/references/wan30-prompt-spec.md)）
2. **画面文字纪律**：含台词或心声片段，【公共总规范】必须有 `画面文字纪律：` 统一无字幕句，逐字取自 [wan30-adapter 4.2 第 5 块](../short-drama-workflow/references/wan30-adapter-v1.0.md)（R39／TEXT-03）
3. **声线锁定**：含人声音频的片段公共层有 `声线锁定：` 行，逐字取自声线母版（[voice-and-dubbing](../short-drama-workflow/references/voice-and-dubbing.md)）
4. **时间轴结构**：0.5 秒粒度、首尾相接、硬切显式、镜头词前置 30%（由机检强制）
5. **原文覆盖**：交付前跑覆盖率，逐字命中 <0.99 的差异人工核对一次
6. **一轮通读合评**：机检抓不住的语义错误靠 [合评清单](references/lean-checks.md) 这一遍

## 流水线（A→F，单会话直通）

| 阶段 | 做什么 | 引用的完全体文件 | 预算 |
|---|---|---|---|
| A 输入登记 | 迷你输入单：源文件/版本哈希/画风/轨/范围 | [project-brief](../short-drama-workflow/references/project-brief.md) 最小字段 | 2 min |
| B 剧本＋切分 | **单遍直出**：读一遍原文→事件分集＋拍摄剧本＋片段切分＋容量自查一次完成 | [story-evaluation](../short-drama-workflow/references/story-evaluation.md)（评估尺）、[runtime-planning](../short-drama-workflow/references/runtime-planning.md)（估时口径）、[pace-and-hook-spec](../short-drama-workflow/references/pace-and-hook-spec.md)（A 层自查内嵌）、S15 创作指令与知识库 | 10–15 min |
| C 资产 | 角色/场景/道具卡＋声线母版，写法完全照完全体规范 | [prompt-layering](../short-drama-workflow/references/prompt-layering.md)、[asset-image-production](../short-drama-workflow/references/asset-image-production.md)、[character-asset-prompts](../character-asset-prompts/SKILL.md)、[voice-and-dubbing](../short-drama-workflow/references/voice-and-dubbing.md)、[outfit-variants](../short-drama-workflow/references/outfit-variants.md)（命中才读）、S03 拆资产（按需） | 8–12 min |
| D 编译 | 直接写片段级视频提示词：镜头前置、三锚、微表演融进正文；不落独立逐镜表 | [wan30-prompt-spec](../short-drama-workflow/references/wan30-prompt-spec.md)、[wan30-adapter](../short-drama-workflow/references/wan30-adapter-v1.0.md)、小墨 6.3（行内纪律）、[micro-expression-layer](../short-drama-workflow/references/micro-expression-layer.md)、[content-expression](../short-drama-workflow/references/content-expression.md)、W14/W18（命中才读最小集：不出 JSON，正文内嵌初始位/轴线侧/机位）、[fight-router](../short-drama-workflow/references/fight-router.md)＋S18 拆镜与 388（A/B 级打斗段引用） | 10–15 min |
| E 机检＋合评 | `fast_gate.py` 一条命令 → 硬错即修即跑 → [合评清单](references/lean-checks.md) 10 项 | [prompt-review](../short-drama-workflow/references/prompt-review.md)（严重度口径与合评视角浓缩） | 5–8 min |
| F 交付 | `精简制作包.md`（完全体模板原样，字段不变） | [compact-import](../short-drama-workflow/references/compact-import.md)、[模板副本](../short-drama-workflow/assets/drama-compact-package-template.md) | 1 min |

**B/C/D 单遍直出的含义**：不落独立中间文档（无 01/02/04 内部文件、无 03b 评稿、无逐镜表/站位 JSON/三份账）。发现上游错，当场修当前稿，不回滚阶段；交付后用户提的修改走定向改稿同样规则。

## 引用覆盖对照表（完全体必读 → 快速档处置）

| 完全体阶段必读 | 快速档处置 |
|---|---|
| S15 全指令＋知识库（short-drama-rules／screenplay-format／quality-rubric／adaptation-modes／output-profiles） | B 阶段保留引用 |
| story-evaluation／runtime-planning／pace-and-hook-spec（阶段 1＋1.5） | B 阶段保留引用（1.5 门合并为容量自查） |
| prompt-layering／asset-image-production／voice-and-dubbing | C 阶段保留引用 |
| character-asset-prompts、S03 拆资产 | C 阶段按需保留引用 |
| outfit-variants | 命中服装变体才读 |
| micro-expression-layer | D 阶段保留引用（行内纪律＋C 阶段极性基线） |
| 小墨 6.3、W14 组合流程 | D 阶段保留引用（不出中间文档） |
| W18 站位流程／E28 站位 | 合并：命中风险闸门才读最小集，正文内嵌三行（初始位/轴线侧/机位），不落 JSON |
| fight-router、S18 拆镜 3.0、388 打斗 | 命中 A/B 级打斗段保留引用；纯文戏一行豁免 |
| prompt-review | 合并：七视角浓缩为合评清单，严重度口径原样引用 |
| wan30-prompt-spec／wan30-adapter／content-expression | D 阶段保留引用 |
| failure-cases 相关条目 | 红线＋合评清单覆盖 TEXT-02/03、DIALOGUE-01、SPACE-01、SYNC-01 等高频项；其余按需查 |
| Seedance S18 适配器／H3 系 skill | 豁免（本档固定 Wan3.0） |
| compact-import／模板／校验脚本 | F 阶段保留（脚本由 fast_gate 封装） |
| 站位交叉校验机检 | 豁免＋已知弱点标注：快速档无站位目录，靠正文内嵌三行；4+ 人或风险闸门场景多的项目应升级完全体 |
| 覆盖率脚本 | fast_gate 第 3 步封装 |
| 阶段 6 视频遵循检查 | 豁免：残余生成问题走编辑指令级修复，系统性失败触发升级条款 |

## 可选开关

`--sample-first`（默认关）：先实际生成 1–2 个代表性片段（一场对话＋一段动作）验证模型行为（身份/字幕/站排），再出全包。高危段多或首次使用本档画风的项目建议开启。

## 升级条款

- 生成端出现**系统性**失败（身份漂移、字幕复发、站排）→ 受影响段落升级走完全体流程重做；失败指纹记入 [lean-checks 附录](references/lean-checks.md)；
- 连续两个项目同一指纹 → 向用户报告并建议把防错规则回写完全体（不在快速档加规则）；
- 项目 >3 集或含 3 场以上 A 级打斗 → 建议直接用完全体。

## 防膨胀条款

- 本 skill 自有流程规则硬顶 **10 条**（清单见 [lean-checks](references/lean-checks.md)）；增删需用户批准；每季度复扫，两轮未触发的规则降级为机检静默检查；
- 本 skill 文件禁止出现写作规范正文，禁止改写字段格式——发现完全体规范缺口，报告用户走完全体修订路径（如 TEXT-03 模式）。
