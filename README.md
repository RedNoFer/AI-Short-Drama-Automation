# AI 短剧自动化（AI-Short-Drama-Automation）

ZHIFEIJI AI 影视创作资源库：21 组影视创作 Skill 源文件 + 四个工作流导航 Skill（资源路由、角色资产美工、短剧工作流、MiniMax H3 提示词）。

仓库地址：<https://github.com/RedNoFer/AI-Short-Drama-Automation>（公开）

## 目录结构

| 路径 | 内容 |
| --- | --- |
| `AGENTS.md` | 本目录协作规范（入口） |
| `.agents/skills/` | 导航与工作流 Skill：`zhifeiji-workflow-router`、`character-asset-prompts`、`short-drama-workflow`、`minimax-h3-adapter` |
| `01 ~ 25` | 原始影视创作资源（角色捏人、分镜、资产提取、出图、构图、Seedance、机甲、正反打、剧本诊断、打斗、真人感微表情、minimax H3 官方 skill 等）；`25 minimax H3官方skill/` 为官方原样副本，来源见 `25 minimax H3官方skill/来源说明.md` |
| `补充资源/` | 补充导入的源文件（小墨个人分镜 SKILL 6.3 原版、Wan3.0 手册学习笔记等） |
| `Wan3.0视频创作者手册.md` | Wan3.0 视频创作参考手册 |
| `ZHIFEIJI｜白模预演固定替换模板_v1.0.pdf` | 白模预演模板 |

## 使用方式

先读 `AGENTS.md`，再按需进入 `.agents/skills/zhifeiji-workflow-router/SKILL.md` 选择对应源文件。

需要 MiniMax H3 结构的视频提示词时，走 `.agents/skills/minimax-h3-adapter/SKILL.md`（组合流程 W17）。

短剧工作流默认 Seedance 2.5，另有 Wan3.0 与 MiniMax H3 两个 profile；总流程见 `.agents/skills/short-drama-workflow/references/workflow-spec.md`，三轨差异与“只拆分支层”的边界见 `model-branch-matrix.md`。Seedance 2.0 的 S02/S07/S13 是独立路由族，不并入 30 秒多镜主线。

## 下载与克隆

仓库本体：git pack 约 53MB，解压后约 82MB（不含演示视频），可直接克隆：

```bash
git clone https://github.com/RedNoFer/AI-Short-Drama-Automation.git
# 或
git clone git@github.com:RedNoFer/AI-Short-Drama-Automation.git
```

**网络较慢时**（GitHub 直连带宽通常只有几十 KB/s），按下面任选一种方式：

1. 走代理（把地址换成你自己的代理端口）：

   ```bash
   git config --global http.proxy http://127.0.0.1:10900
   git config --global https.proxy http://127.0.0.1:10900
   ```

2. 走 SSH 443 端口（22 端口不通时用），在 `~/.ssh/config` 加：

   ```
   Host github.com
     HostName ssh.github.com
     Port 443
     User git
     IdentityFile ~/.ssh/<你的私钥>
   ```

3. 只要源码不要 git 历史：

   ```bash
   git clone --depth 1 https://github.com/RedNoFer/AI-Short-Drama-Automation.git
   ```

4. 直接下压缩包：仓库页 → `Code` → `Download ZIP`
   （或 <https://codeload.github.com/RedNoFer/AI-Short-Drama-Automation/tar.gz/refs/heads/main>）

## 演示视频附件

10 个 Skill 演示视频（约 196MB）体积较大，已从 Git 历史中移除，改放在 Release 附件里：

<https://github.com/RedNoFer/AI-Short-Drama-Automation/releases>

下载命令示例：

```bash
gh release download v1.0-skills --repo RedNoFer/AI-Short-Drama-Automation
```

## 不纳入版本控制的本地输出

以下目录属于本地生成物，已在 `.gitignore` 中排除，不随仓库提交：

`创作输出/`、`审查输出/`、`生成输出/`、`整改输出/`、`outputs/`、`视频拆解_*/`

演示视频 `*.mp4` 同样已排除在仓库之外（见上方 Release 附件）。
