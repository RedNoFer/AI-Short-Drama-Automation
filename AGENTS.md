# 本目录协作路由

本目录保存 ZHIFEIJI 影视创作资源。新任务由总控定位、组合资源时，先读取[影视工作流导航](.agents/skills/zhifeiji-workflow-router/SKILL.md)，再按导航选择准确源文件与工作流。源文件路径以[资源索引](.agents/skills/zhifeiji-workflow-router/references/resource-map.md)为准；不要按目录名猜文件，也不要默认加载全部资源。已按隔离规范收到批次卡和 manifest 的执行员，按清单读取本批资料，不重复全局路由；发现必需依赖缺失或冲突时报告总控。

## 工作流入口

- 小说改编并制作完整短剧包：读取[短剧工作流](.agents/skills/short-drama-workflow/SKILL.md)。阶段流程、验收、交付和模型分支细则以该 Skill 及其引用的分支策略文件为准。
- 人物资产提示词、美工或建模参考：先按导航选定原始模块，再读取[角色资产提示词技能](.agents/skills/character-asset-prompts/SKILL.md)及当前任务需要的参考文件。
- 用户明确指定 MiniMax H3 结构：读取[H3 提示词分支](.agents/skills/minimax-h3-adapter/SKILL.md)及其引用的素材规范。
- 其他模块与专项流程（包括 E24/W14、E28/W18、服装变体）：由影视工作流导航按任务选择，只读取命中的文件。
- 执行短剧批次隔离或并行任务：遵循[多智能体隔离执行规范](.agents/skills/short-drama-workflow/references/multi-agent-execution.md)。

## 通用边界

- 用户本轮明确给出的模型、画幅、范围和交付要求优先；具体创作规则以选定 Skill／分支文件为准，不在本文件复制参数或验收细则。
- 保留原始资源；新创作结果保存到指定的创作输出位置，并与导航及源文件分开。
- 若路由、源文件或派单清单缺少完成任务所需的规范，停止受影响的工作并报告总控，由总控补齐路由或清单后继续；不要猜路径、扩大读取范围或让用户裁决内部清单问题。
