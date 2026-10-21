---
name: minimax-h3-adapter
description: 当用户要求使用 MiniMax H3（海螺 H3 / minimaxh3 / H3 结构）的提示词结构时，走本分支：先按 H3 口径做分镜与时间轴，再编译成 H3 的结构化视频提示词（base 三字段或 Ref2VA 六段式），并把本目录资产 ID 映射为 <Subject>/<Picture>/<Video>/<Audio> 参考标签。触发语：minimaxh3、MiniMax H3、海螺 H3、H3 提示词结构、H3 结构、按 H3 格式写提示词、Ref2VA、T2VA/I2VA/FL2VA/L2VA。
compatibility: 仅做路由与适配说明，不调用外部 API；官方原文位于 25 minimax H3官方skill/。
---

# MiniMax H3 提示词分支（E27）

本分支只替换**最终视频提示词的格式层**（分镜时间轴写法 + 提示词结构），不替换剧本、资产、角色与场景设计，也不覆盖短剧工作流的其他阶段。
官方原文（不改写、不改格式）：

| 用途 | 绝对路径 |
|---|---|
| 官方 Skill 主文件 | `/Users/a1/work/3000课程21个skill/25 minimax H3官方skill/skills/h3-prompt-writing/SKILL.md` |
| base 模式指南（T2VA/I2VA/FL2VA/L2VA） | `/Users/a1/work/3000课程21个skill/25 minimax H3官方skill/skills/h3-prompt-writing/references/base-en.txt` |
| 全参考模式指南（Ref2VA） | `/Users/a1/work/3000课程21个skill/25 minimax H3官方skill/skills/h3-prompt-writing/references/ref-en.txt` |
| 官方 9 个 Skill 与安装说明 | `/Users/a1/work/3000课程21个skill/25 minimax H3官方skill/skills/README.md` |

**规则优先级**：官方 txt 原文 > 本适配说明 > 本目录其他模块的默认写法。冲突处按下面「冲突裁决」处理，并记录原因。

## 何时进入本分支

- 用户明确说「用 minimaxh3 / H3 的提示词结构」「按 H3 格式」「海螺 H3」「Ref2VA / T2VA / I2VA / FL2VA / L2VA」。
- 用户给出 H3 官方字段名（`integrated_multimodal_description`、`overall_soundscape`、`non_diegetic_music`、`subject_definitions`、`retention_analysis` 等）。
- 用户点名 H3 官方 Skill 名称。

**不进入**：用户只说「视频提示词」「Seedance」「可灵」而未指定 H3 时，走既有 F 组路由（S02/S07/S08/S13/S18/S21）与 W14/W16，不改用 H3 结构。用户之前说过一次 H3 不等于后续默认 H3；每次仍按当次要求判断。

## 分支流程（W17）

### 1. 判定模式

| 用户提供 | 模式 | 输出结构 |
|---|---|---|
| 只有文字/剧情/分镜 | **T2VA** | base 三字段 |
| 一张首帧图 | **I2VA** | base 三字段＋首帧对齐指令行 |
| 一张首帧图＋一张尾帧图 | **FL2VA** | base 三字段＋双图对齐指令行（默认单镜头） |
| 只有一张尾帧图 | **L2VA** | base 三字段＋尾帧对齐指令行 |
| 多模态全参考（图/视频/音频混用） | **Ref2VA** | 六段式 |

官方输入上限：图片 ≤9、视频 ≤3（每段 2–15 秒，总时长 ≤15 秒）、音频 ≤3（每段 2–15 秒，总时长 ≤15 秒），跨类型文件总数 ≤12。超限时先与用户确认取舍，不静默丢弃参考。

用户不给模式但给了参考素材时，按上表判定并**在交付中写明所用模式**；素材形态不明（例如“用这张图”）时按 I2VA 处理并在正文前说明。

### 2. 分镜分支（H3 口径）

先做分镜与时间轴，再编译提示词。分镜字段：

- 镜头编号与切点：`[Shot 1]`（**不带时间戳**）、`[Shot 2] At 00:03.500, ...`，切点严格递增且落在成片时长内。
- 每镜：构图与景别、主体与位置、环境与光线、动作与结果、运镜（类型＋幅度＋速度，写成自然英文句子）、同期声、说话人 ID 与台词原文、参考标签首次出现点、入口/出口状态。
- 对白跨切：两段都写 `<scenetrans>` 并说明声音跨切延续；被成片截断用 `<cutoff>`。
- 画外音：写 `says in an off-screen voiceover` 并紧跟「嘴唇保持闭合」句。
- 画面可见文字：双引号原样保留（如 `"营业中"`），不翻译。
- 说话人 ID：`(S1)`、`(S2)`、合唱 `(S1,S2)`；同一说话人跨镜沿用同一 ID；不发声角色不分配 ID。

分镜层可直接沿用本目录既有能力：S03 稳定资产 ID、S02 精细拆镜、E24 小墨 6.3 视感与镜头经济性、S18 动作因果链、E25 微表情表演层。**只借镜头设计与表演层字段，最终提示词正文必须写成 H3 结构**，不与 S18/S21 模板混写。

时长口径：H3 单条成片 **4–15 秒**（官方指南）。本目录短剧工作流默认 30 秒片段，两者冲突按「冲突裁决」处理。

### 3. 编译提示词

**base 模式**（T2VA/I2VA/FL2VA/L2VA）：

1. I2VA 首行固定句式：
   `For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.`
2. FL2VA 首行固定句式：
   `How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot N) aligns with the S.SS-second mark of the target video.`
3. L2VA 首行固定句式：
   `How the reference pictures align with the target video — <Picture 1> (from Shot N) aligns with the S.SS-second mark of the target video.`
   （T2VA 无对齐指令行，直接从字段开始；指令行后空一行再写字段。）
4. 三字段固定顺序与名称：

```text
integrated_multimodal_description: [Shot 1] ...

overall_soundscape: ...

non_diegetic_music: ...
```

- `integrated_multimodal_description`：沿时间轴写画面、动作、镜头、说话人、台词、唱歌与同期声；`[Shot 1]` 处先给整体风格与初始构图。
- `overall_soundscape`：1–4 句连续段落，概括全片环境声、动作声、非语言人声；台词/唱歌/剧情内音乐不在此重复；全片静音才写 `N/A`。
- `non_diegetic_music`：1–3 句，写角色听不到的观众侧配乐（配器、速度、节奏、动态变化）；无则 `N/A`。

**Ref2VA 模式**：六段固定顺序
`subject_definitions` → `summary` → `retention_analysis` → `detailed_description` → `overall_soundscape` → `non_diegetic_music`。
标签四类：`<Subject N>`（可复用可见内容）、`<Picture N>`（参考图/帧锚点）、`<Video N>`（参考视频）、`<Audio N>`（参考音频）；标签一经定义全文一致。`detailed_description` 生成类任务官方建议 350–500 英文词；风格说明写在 `[Shot 1]` 之前的一两句。

**语言规则**：改写段落一律英文；台词、歌词、画面可见文字保留原语言并逐字照抄（含标点）。用具体视听细节，不用 `cinematic`、`beautiful` 这类空词。

### 4. 本目录资产 → H3 参考标签映射

| 本目录对象 | H3 标签 | 规则 |
|---|---|---|
| 角色/场景/道具资产条目（`@CH-001`/`@SC-001`/`@PROP-001`、`CHAR_`/`LOC_`） | `<Subject N>` | 定义一次，全文复用；同一主体可由多份素材共同定义 |
| 实际已上传的参考图/首帧/尾帧 | `<Picture N>` | 编号与上传顺序一致；**未上传的真实图片不得预写编号** |
| 参考视频 | `<Video N>` | 用于剪辑源、续接起点或整片时间结构 |
| 参考音频 | `<Audio N>` | 区分 `fully_copy`（整轨复用）与 `reference`（仅音色/节奏参考） |

没有真实图片时，正文只写资产代码与可见不变量（外观职责、服装版本、地标与光向），并在交付说明中标注「参考图未上传，未建立 `<Picture N>` 映射」。不把编号当成已存在的图像输入。

### 5. 质量检查

机检（只证明格式，剧情与表演仍由 agent 判断）：

```bash
python3 "/Users/a1/work/3000课程21个skill/.agents/skills/minimax-h3-adapter/scripts/audit_h3_prompt.py" 提示词文件.md --duration 15 --mode fl2va
```

人工复核（不可省略）：
- 描述总时长与目标成片一致（4–15 秒），切点全部落在时长内且递增。
- 字段名、顺序、标签、说话人 ID、`<d>` 语言标签与官方指南逐字一致。
- 每个镜头都有动作结果与声音归属；台词跨切/画外音/可见文字按官方写法处理。
- 参考标签全文一致、无悬空标签；时长、画幅、清晰度等生成参数不写进正文（由应用设置承载）。
- 提示词审稿按本目录 [提示词质量规范](../short-drama-workflow/references/prompt-review.md) 视角复核（剧情因果、表演可拍性、空间衔接、声音来源），H3 结构通过不等于内容通过。

## 冲突裁决

| 冲突 | 裁决 |
|---|---|
| H3 单条 4–15 秒 vs 本目录短剧工作流默认 30 秒片段 | 用户指定 H3 结构即以 H3 为准：把 30 秒片段在**分镜阶段**切成 ≤15 秒的 H3 条（如 15+15），边界按剧情节拍落刀；用户已固定 30 秒边界时，先说明该条无法用单条 H3 覆盖，给出拆分方案再动手 |
| H3 单条 ≤15 秒 vs W14 的 30 秒/6–8 镜/5–7 硬切 | 硬规按 H3 侧重新配平：镜头数与切点数按 4–15 秒可执行的密度给，不强行凑 5–7 切；保留每镜信息职责 |
| 本目录 2000/3000/4500 字符上限（S18 轨） | H3 轨不套用该上限；按官方词数口径（Ref2VA 生成类 350–500 词；base 模式以「一镜一动作一声音」写实为准），接口更严时以接口为准 |
| S18/S21 提示词模板 | H3 轨只交付一套 H3 正文，不并列输出两套模板；需要 Seedance 版本时另起一条轨 |
| 官方 h3-prompt-writing 只有英文版 | 正文英文、台词保留原语言属官方要求，不是改写；不擅自补写官方不存在的中文版规则 |
| 8 个风格 Skill | 面向 MiniMax Hub canvas 工作流，不是通用 agent 流程；用户点名风格时读对应 `SKILL.md`/`SKILL.cn.md` 作为风格约束，不作为 H3 结构来源 |

## 交付

H3 轨默认交付：①模式与依据（哪些参考素材、实际时长）②分镜与时间轴表 ③H3 提示词正文（base 三字段或 Ref2VA 六段式）④未解决项与假设（参考图缺失、未确认背面、时长冲突处理）。在短剧工作流上下文中仍按精简制作包结构交付，正文字段换成 H3 结构并说明差异。

## 交接

记录：模式（T2VA/I2VA/FL2VA/L2VA/Ref2VA）、成片时长与片段边界、资产 ID → `<Subject N>` 映射、实际上传素材 → `<Picture/Video/Audio N>` 映射、说话人 ID 表、每镜切点与台词归属、与既有 Seedance/Wan 轨的差异说明。
