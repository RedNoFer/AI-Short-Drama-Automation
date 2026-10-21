# AI 短剧自动化

ZHIFEIJI AI 影视创作资源库：21 组影视创作 Skill 源文件 + 三个工作流导航 Skill（资源路由、角色资产美工、短剧工作流）。

## 目录结构

| 路径 | 内容 |
| --- | --- |
| `AGENTS.md` | 本目录协作规范（入口） |
| `.agents/skills/` | 导航与工作流 Skill：`zhifeiji-workflow-router`、`character-asset-prompts`、`short-drama-workflow` |
| `01 ~ 24` | 21 组原始影视创作资源（角色捏人、分镜、资产提取、出图、构图、Seedance、机甲、正反打、剧本诊断、打斗、真人感微表情等） |
| `补充资源/` | 补充导入的源文件（小墨个人分镜 SKILL 6.3 原版、Wan3.0 手册学习笔记等） |
| `Wan3.0视频创作者手册.md` | Wan3.0 视频创作参考手册 |
| `ZHIFEIJI｜白模预演固定替换模板_v1.0.pdf` | 白模预演模板 |

## 使用方式

先读 `AGENTS.md`，再按需进入 `.agents/skills/zhifeiji-workflow-router/SKILL.md` 选择对应源文件。

## 不纳入版本控制的本地输出

以下目录属于本地生成物，已在 `.gitignore` 中排除，不随仓库提交：

`创作输出/`、`审查输出/`、`生成输出/`、`整改输出/`、`outputs/`、`视频拆解_*/`
