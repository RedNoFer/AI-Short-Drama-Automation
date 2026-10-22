# 红喵导演台 SCENE_JSON

使用无注释的有效 JSON，坐标和尺寸单位为米。

```json
{
  "version": "1.0",
  "scene": {"name": "仓库对峙", "environment": "废弃仓库", "time": "夜晚", "scale": "meters"},
  "characters": [
    {
      "id": "char_guard",
      "name": "守卫",
      "color": "#d84a3a",
      "position": [0, 0, 0],
      "facing": 0,
      "posePreset": "fight",
      "poseControls": {},
      "bodyType": "standard",
      "weapon": "ak15k-rifle",
      "scale": 1,
      "labels": ["主体"],
      "movementPath": [[0, 0, 0], [1.2, 0, -1.5]]
    }
  ],
  "props": [],
  "camera": {
    "shot": "平视中景",
    "lensMm": 48,
    "fov": 48,
    "position": [5.8, 1.6, 6.6],
    "target": [0, 1.1, 0],
    "movement": "缓慢推近",
    "aspectRatio": "16:9",
    "bodyView": "hands",
    "handView": "both"
  },
  "lighting": {"key": "左后方冷色主光", "fill": "右前方弱补光", "mood": "紧张"},
  "continuity": ["人物与武器身份不变"],
  "characterPathDuration": 4,
  "directorAnnotations": []
}
```

## 人物字段

- 必需：`id`、`name`、`color`、`position`、`facing`。
- `posePreset`：使用 Skill 中列出的新版姿势。
- `poseControls`：可选关节对象；支持身体、躯干、头、肩、肘、手、髋、膝、脚的角度控制。
- `weapon`：可选，只能使用 `longsword`、`knife`、`parang`、`spear`、`baseball-bat`、`g21-pistol`、`ak15k-rifle`。
- `bodyType`：`standard`、`slim`、`strong`、`child`、`giant`。
- `movementPath`：可选位置点数组，至少两点才能预演。
- `locked`：可选布尔值，锁定后禁止移动、旋转、删除和属性修改。

朝向：`0` 朝 `-Z`，`1.5708` 朝 `-X`，`-1.5708` 朝 `+X`，`3.1416` 朝 `+Z`。

## 道具字段

- `kind`：`table`、`chair`、`bench`、`cup`、`tree`、`lamp`、`device`、`box`。
- `size`：`[长度X, 高度Y, 宽度Z]`。
- `box.semanticType`：`block`、`wall`、`door`、`window`、`step`、`bed`、`sofa`、`vehicle`。

## 镜头字段

- `aspectRatio`：`auto`、`1:1`、`2:1`、`3:4`、`4:3`、`16:9`、`21:9`、`9:16`。
- `bodyView`：仅 `hands` 或 `none`。
- `handView`：`left`、`right`、`both`。
- `keyframes`：可选机位点，每点包含 `position`、`target`、`fov`、`time`。
- `motionRegion`：可选，包含 `center`、`radius`、`startDistance`、`endDistance`、`cameraHeight`、`azimuth`、`preset`。

## 导演标记

`directorAnnotations` 中 `tool` 可为 `pen`、`arrow`、`text`；点坐标为画布归一化的 `0–1`。
