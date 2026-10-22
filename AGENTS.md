# 本目录协作规范

本目录保存 ZHIFEIJI 的 21 组 AI 影视创作源资源。

当用户希望定位、组合或使用本目录资源来做小说改编、剧本、角色/服饰/机甲资产、电影感图片、场景多视角、分镜、表演或视频运镜时，先读取：
[影视工作流导航](.agents/skills/zhifeiji-workflow-router/SKILL.md)。

按该技能的路由选择源文件；准确路径见：
[源 Markdown 文件索引](.agents/skills/zhifeiji-workflow-router/references/resource-map.md)。
不要仅按目录名推测文件名，也不要默认加载全部 21 组原文。

保留原资源，除非用户明确要求修改。新创作结果与导航文件分开保存。
该导航不改变与影视资源无关任务的工作方式；用户当前明确要求优先。

## 人物资产美工与建模参考补充

处理人物资产提示词、角色美工优化、五官/妆发/服装材质深化、人物三视图或建模参考时，在导航选定主模块后读取：
[角色资产美工与建模提示词](.agents/skills/character-asset-prompts/SKILL.md)。

该技能作为人物美术补充层；只按当前任务读取其设计、建模验收及本地衔接参考。保留已确认身份、年龄感、物种、画风、角色ID和未授权修改项；把美工提升写成具体结构、剪裁、材质与配色，不只堆“绝美、电影感、8K”。

本目录通用人物建模参考板默认16:9白底、左正面身份特写＋右完整正/左侧/背全身；用户、当前项目或明确选定原版技能的版式优先。美型CG不因质量提升自动转真人；S16高写实转换沿用已有锁脸状态，未确认先做身份开发，不重复请求已有确认。

提示词、图片候选、已确认基准和实际3D模型分开记录；文字优化不触发媒体生成。提案与不可见背面补全注明来源状态，不伪造参考图或确认结果。原始导入ZIP保存在`补充资源/角色资产生成skill.zip`。

## 短剧工作流Skill

用户只提供小说与目标短剧风格/画风，希望系统自行推算集数、时长、片段并完成剧本、资产设计、分镜及全部视频提示词时，读取[短剧工作流Skill](.agents/skills/short-drama-workflow/SKILL.md)。该技能以本目录导航和原始模块为依据，默认每条视频片段 30 秒、6–11 镜、**5–10 次硬切**，每条视频提示词不超过 3000 Unicode 字符（第二档默认；第一档紧凑 2000、第三档试点 4500，具体数值以其 policy.json 为准）；人物资产提示词为 16:9 四视图，场景资产提示词为 16:9 全景。**当前最终只交付一个符合[固定精简制作包模板](.agents/skills/short-drama-workflow/assets/drama-compact-package-template.md)的 `创作输出/作品名/精简制作包.md`**；在线原件地址和本地副本已写在 Skill 中，用户无须重发。模板只导入资产图片提示词，不携带实际图片或内部剧本/分镜/QC 文件。剧情、资产、分镜和提示词在各自写作时应用质量规范、交接前评价；每批导出后由脚本校验导入结构、字符数、时间轴、资产代码绑定、镜头编号和硬切（按轨选择 `--model seedance25|wan30|h3` 与 `--tier`），再由 agent 独立复核剧情、表演和画面质量，整改复评；未生成的视频不得标为遵循提示词验收通过。

## 小墨 6.3 分镜补充

用户指定小墨个人分镜 Skill 6.3 时，读取[原版文件](补充资源/小墨个人分镜SKILL6.3（豪华升级版）.md)与导航中的 E24；原版文件保持不改。独立执行 W14 时按用户给的片段时长、画幅和清晰度；从短剧工作流 Skill 进入时，先由系统按小说剧情和表演估时提出并记录规格，再按[W14 组合流程](.agents/skills/zhifeiji-workflow-router/references/workflows.md#w14)执行。片段边界与镜头归属随分镜规划确定，用户已指定的边界直接沿用；时间码另记且只用整数秒，最终正文由 S18 的 Seedance 2.5 适配器生成。保留小墨原版的短剧视感和空间切镜规则。

## MiniMax H3 提示词分支

用户要求使用 MiniMax H3（海螺 H3 / H3 结构 / minimaxh3）的提示词结构时，读取[H3 提示词分支](.agents/skills/minimax-h3-adapter/SKILL.md)、[H3 素材引用规范](.agents/skills/minimax-h3-adapter/references/asset-reference.md)与导航中的 E27，并按[W17 组合流程](.agents/skills/zhifeiji-workflow-router/references/workflows.md#w17)执行：先按 H3 口径做分镜与切点时间轴，再编译成官方 base 三字段或 Ref2VA 六段式正文。官方原文原样保存在`25 minimax H3官方skill/skills/`（`h3-prompt-writing/SKILL.md`、`references/base-en.txt`、`references/ref-en.txt`），不得改写；本地只做路由、资产映射（`@CH/@SC/@PROP` → `<Subject N>`，编号按角色→场景→道具顺序从 1 连续）与冲突裁决。

H3 轨片段不额外拆，时长沿用目标应用的片段单位（默认 30 秒），正文用官方固定格式写完整时间轴（官方 4–15 秒是模型单条输出上限，属生成侧登记事项）；H3 轨不套用 S18 的 2000/3000/4500 字符档（官方未设字符上限，本项目硬顶 6000 字符、低于 1200 提醒过简，硬切带 0–6 次），最终正文只交付一套 H3 结构，不与 Seedance/Wan 模板并列。正文原样写入精简制作包的 `#### 视频提示词` 块，机检用 `validate_compact_package.py <包> --model h3`。未上传的真实图片不得预写 `<Picture N>`。8 个官方风格 Skill 面向 MiniMax Hub canvas 工作流，用户点名时才读取；本目录无该运行时，只能读风格与流程规范，生成步骤不得声称已执行。

## 站位空间真值分支

多人共处、固定座位、狭小室内、站位易错或需要可计算机位时，读取导航中的 E28（`26站位图+skill/站位Skill/hongmiao-director/SKILL.md`，原文件保持不改）并按[W18 组合流程](.agents/skills/zhifeiji-workflow-router/references/workflows.md#w18)执行：阶段 2 为命中风险闸门的场景出 `SCENE_LOC_*.json` 基底，阶段 3 为命中同一闸门的镜头出镜级增量 JSON，overlay 必须先于该镜分镜文字产出，机检用 `validate_space_blocking.py`。坐标以地标与固定结构为真值锚点，交付包只带自然语言站位描述、不带数值与图片编号。**本目录无红喵导演台运行时，只出 SCENE_JSON 与文字站位，不渲染 3D 站位图、不产出或批准写实剧照**；`26站位图+skill/` 下的 PNG 仅为语义样本。

