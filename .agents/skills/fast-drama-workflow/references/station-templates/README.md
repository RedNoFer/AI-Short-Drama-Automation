# 站位基底原型模板（快速档）

两个已通过 `validate_space_blocking.py` 六项机械校验（0 错误 0 警告）的场景原型。用途：命中站位风险闸门（多人同框≥2、固定座位、狭小室内、操作位）的场景，C 阶段**复制→改名→改坐标**即得站位基底，不再从零建模。

| 文件 | 原型 | 典型场景 |
|---|---|---|
| `SCENE_LOC_xx_桌位双人直播位.json` | 固定桌位·双人对坐/并坐直播 | 直播带货、访谈、对饮、办公桌对话 |
| `SCENE_LOC_yy_机械列车间.json` | 设备列·多人分区站立 | 车间、后厨、仓库、机房等设备场景 |

`overlay_示例_*.json` 是镜级增量的填法示例（含 movementPath 走位与转场朝向改写），**不要**复制进项目站位目录。

## 使用步骤

1. **复制改名**：基底复制到 `<作品目录>/内部/04b-站位图/SCENE_LOC_xx.json`（xx 与精简制作包的场景代码一致）；镜级增量命名 `E{集}_SH{xx}_S{镜序}.json`。
2. **替换占位**：`LOC_xx`→实际场景代码；`CHAR_01/CHAR_02/CHAR_05/WORKER_x`→实际角色代码与姓名；`environment` 按实际场景改写（固定结构与左右关系是唯一真值）。
3. **改坐标**：桌/椅/设备位置按实际尺寸与朝向挪动；**facing 不用手算**——按 `facing = atan2(-(tx-x), -(tz-z))`（0 指向 -Z）由 facingTarget 派生，或直接改 facingTarget 交给脚本校验。
4. **自检**：`python3 .agents/skills/short-drama-workflow/scripts/validate_space_blocking.py <作品目录>/内部/04b-站位图`——0 错误才编译正文；站位继承表用 `build_blocking_table.py` 生成（stdout 重定向落盘）。
5. **机检**：fast_gate 自动探测 `内部/04b-站位图` 并挂 `--space-dir` 交叉校验，无需手动传参。

## 坐标与字段要点（来自校验器实测规则）

- 净距：角色与可移动实体（table/chair/bench/cup/tree/lamp/device/box）水平距离 **≥0.35m**；自己的座椅（`seatFor`/`supportSurfaceId`）、手持物（`heldBy`）、声明接触（`touching`/`serves`）豁免。
- **坐姿**：`posePreset:"sit"` 的 y＝座面高（模板 0.45），且 1.2m 内必须有 chair/bench；`supportSurfaceId` 指向座椅时角色 XZ 必须落在座椅水平范围内、y 与座面顶差 ≤0.02。
- **facing 与 facingTarget 必须一致**；转场改朝向时两个都改。
- **镜级增量存全量角色状态**（不是差量）——基底改了坐标，该镜的 overlay 要同步。
- `movementPath` 两点以上，不得穿过 table/device/chair 等阻挡类道具。
- `window/wall/sofa/bed/vehicle` 属墙类，不参与净距判定；头顶结构（y≥1.5 且厚≤0.35）不算脚下冲突。
- 背景群演策略：工人/路人**不建角色卡**，在基底与锁定句里按"服装特征+固定点位"定位（模板 B 的 WORKER_A/B 即此用法）。

## 与快速档流程的关系

- C 阶段：命中闸门场景复制本模板出基底。
- D 阶段：按已冻结的镜头表出镜级增量（只写相机 position/target/fov、谁进画谁画外、movementPath、承托变化）。
- E 阶段：fast_gate 自动挂 `--space-dir` 交叉校验；未建目录且输入单未登记「站位层：豁免」＝硬错（2026-11-07 起）。
