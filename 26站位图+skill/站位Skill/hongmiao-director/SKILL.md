---
name: hongmiao-director
description: 将中文或英文场景构想转换为红喵导演台可直接粘贴的 SCENE_JSON 与 AI 视频提示词。用于人物站位、姿势与逐关节控制、七类本地武器及动作适配、人物行动路径、道具、镜头、运镜、画幅、灯光、连续性、导演俯视图或场景数据修复。
---

# 红喵导演台

把简短剧情转换为可拍摄、可编辑、可直接粘贴进最新版离线红喵导演台的场景方案。

生成或修复 JSON 前读取 [scene-schema.md](references/scene-schema.md)。涉及武器时必须读取 [weapon-library.md](references/weapon-library.md)。

## 工作流

1. 提取场景、人物关系、关键动作、武器、道具、视角、光线和剧情重点。
2. 先安排人物位置与朝向，再安排支撑物和环境道具，最后确定镜头、光线及连续性。
3. 为每个人物选择受支持的 `posePreset`；精确动作才补充 `poseControls`。
4. 根据动作语义从武器库选择唯一稳定的 `weapon` ID；用户明确指定时以用户选择为准。
5. 检查落地、坐姿支撑、穿模、遮挡、人物距离、行动通道、武器握持和画幅安全区。
6. 按固定四段格式输出。

## 空间与姿势

- 地面为 `y=0`，`+Y` 向上，主要行动区靠近 `[0,0,0]`。
- 人物正面朝向目标 `[tx,tz]`：`atan2(-(tx-x), -(tz-z))`。
- 支持的姿势：`stand`、`t-pose`、`walk`、`run`、`sit`、`lie`、`crouch`、`kneel-one`、`kneel-two`、`hands-on-hips`、`lean`、`bow`、`think`、`fight`、`kick`、`throw`、`push`、`wave`、`reach`、`cross-arms`、`phone`。
- 坐姿必须匹配椅子或长凳；倒地人物贴近地面；站立和奔跑人物至少有一只脚可靠接地。
- 人物与实体道具通常保留至少 `0.35m` 间隙，动作通道不得穿过墙体或主要道具。

## 武器

- 仅使用新武器 ID：`longsword`、`knife`、`parang`、`spear`、`baseball-bat`、`g21-pistol`、`ak15k-rifle`。
- 不再生成旧 ID `sword`、`staff`、`pistol`；导演台仅为旧场景自动迁移它们。
- 依据 [weapon-library.md](references/weapon-library.md) 的动作映射选择武器。没有明确武装语义时省略 `weapon`，不要自动给日常人物或未成年人配武器。
- 持枪、持矛和挥砍动作应让胸腔、右肩、右肘及右手方向一致，武器不得穿过身体。

## 镜头与路径

- `camera.aspectRatio` 可为 `auto`、`1:1`、`2:1`、`3:4`、`4:3`、`16:9`、`21:9`、`9:16`。
- 第一视角 `bodyView` 仅使用 `hands` 或 `none`；`handView` 可为 `left`、`right`、`both`。
- 人物位移使用 `movementPath`，至少两个 `[x,y,z]` 点；顶层用 `characterPathDuration` 指定时长。
- 连续运镜使用 `camera.keyframes` 与 `camera.pathDuration`；路径应避开墙体和演员动作区。

## 输出格式

严格依次输出：

1. `【布局摘要】`：主体、景别层次、行动关系和镜头重点。
2. `【AI视频提示词】`：环境、人物动作与站位、武器、道具、镜头、光线和连续性。
3. `【假设与风险】`：关键假设及遮挡、碰撞、支撑、出画风险。
4. `SCENE_JSON`：无注释的有效 JSON。

## 交付检查

- JSON 包含 `scene`、`characters`、`props`、`camera`、`lighting`、`continuity`。
- 只生成新版姿势、武器和第一视角字段。
- 人物落地或坐稳，武器与动作匹配且不穿模。
- 普通提示词、布局摘要、风险说明与 JSON 一致。
