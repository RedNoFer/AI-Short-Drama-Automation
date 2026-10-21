# ZHIFEIJI｜模型三视图设定板生成器 SKILL v1.2

版本标识：v1.2

## 1. 技能定位

本技能用于将用户上传的任意模型图片，自动整理并生成一张专业的「模型三视图技术设定板」。

职责边界：本技能负责带尺寸区、五个细节框、规格表和技术蓝图背景的“模型技术设定板”。若主体是人物、类人角色、异形人物或机械人体，且用户要求“左侧脸部特写＋右侧正面/侧面/背面”的干净人物身份设定板，应改用 `zhifeiji-illustration-to-photoreal-character` 的“人物三视图”模式；不得套用本技能的规格表、尺寸标尺和五个细节框版式。

适用对象包括：

- 科幻机甲
- 机器人
- 载具
- 飞船
- 武器
- 装甲
- 怪兽
- 生物模型
- 雕塑
- 产品模型
- 游戏角色模型
- 影视道具
- 建筑或机械设备

用户只需要上传一张或多张参考图片，不需要额外描述。系统必须自动识别主体，并按照统一版式生成：

1. 正视图
2. 侧视图
3. 背视图
4. 高度或尺寸比例尺
5. 五个局部细节放大框
6. 基础规格信息区
7. 人体或标准比例参照
8. 简洁技术蓝图背景

---

## 2. 默认执行方式

当用户上传图片后，直接执行，不反复追问。

默认回复逻辑：

- 用户只上传图片：直接进入标准三视图生成模式。
- 用户上传图片并说明尺寸：严格使用用户提供的尺寸。
- 用户没有提供尺寸：不虚构精确数据，尺寸栏使用 `N/A`、`ESTIMATED` 或视觉比例展示。
- 用户要求“出图”：直接生成图片。
- 用户要求“提示词”：输出完整可复制提示词。
- 用户要求“出图和提示词”：先生成图片，再输出完整提示词。

---

## 3. 核心任务

### 3.1 主体识别

从参考图中自动识别并锁定：

- 主体类别
- 主体轮廓
- 头身比例
- 装甲结构
- 主色与辅色
- 材质
- 武器与装备
- 标志性结构
- 对称与非对称部分
- 背部结构
- 推进器、背包、尾翼、附件
- 表面编号、纹章、标志
- 机械关节与连接方式

不得随意改变原始设计。

---

### 3.2 三视图生成

必须生成同一模型的三个标准视角：

#### FRONT｜正视图

- 完整正面
- 镜头与主体胸口或结构中心等高
- 无透视夸张
- 双脚或底部落在同一基准线上
- 武器、盾牌、背包不得遮挡主体主要结构
- 保留主体原始轮廓和比例

#### SIDE｜侧视图

- 默认生成左侧视图
- 用户明确要求右侧时，改为右侧视图
- 展示主体厚度、前后结构、背包、尾翼、武器挂载方式
- 不得变成三分之二角度
- 不得出现明显透视变形

#### BACK｜背视图

- 完整展示背部结构
- 保留推进器、背包、机械骨架、尾翼、武器挂点
- 与正视图保持同一高度和比例
- 不得减少、增加或替换核心结构

三个视图必须像同一个实体模型在同一摄影棚中转台拍摄，比例、材质、颜色和零件完全一致。

---

## 4. 隐藏区域推导规则

当参考图只展示一个角度时：

1. 优先依据可见结构进行保守推导。
2. 对称机体按左右对称逻辑补全。
3. 非对称装备必须保留在对应一侧。
4. 不得凭空增加大型武器、翅膀、炮管或装甲。
5. 背部不可见时，只允许依据肩部、腰部、侧面连接结构进行合理延伸。
6. 推导区域必须服从原主体设计语言。
7. 不得把原模型改成另一款机甲、角色、车辆或产品。
8. 不确定的细节宁可简化，也不要胡乱设计。

---

## 5. 标准画面版式

### 默认比例

- 默认画幅：16:9
- 推荐分辨率：3840×2160
- 用户要求宽幅时：21:9
- 背景为深蓝黑、深灰蓝或冷灰技术蓝图背景

### 版面分区

#### 左侧主区域，占画面约 80%

从左到右依次排列：

- 正视图
- 侧视图
- 背视图

三个视图等高、等比例、底部对齐。

#### 左上角

显示：

- `HEIGHT`
- 用户提供的高度
- 或 `ESTIMATED SCALE`
- 垂直尺寸标尺

#### 右侧细节栏，占画面约 20%

竖向排列五个局部放大框：

1. 头部、驾驶舱或前端传感器
2. 胸部、核心结构或主动力区域
3. 盾牌、徽章、纹章或最具辨识度的装甲
4. 武器、机械手、轮组、引擎或功能组件
5. 背包、推进器、尾部或动力结构

每个细节框带编号：

- 1
- 2
- 3
- 4
- 5

每个框下方使用简洁英文功能标签。

#### 底部信息栏

包含两组规格表：

左侧：

- MODEL NUMBER
- TOTAL HEIGHT
- WIDTH
- WEIGHT
- MATERIAL

右侧：

- POWER OUTPUT
- PROPULSION
- SENSOR RANGE
- ARMAMENTS
- SPECIAL EQUIPMENT

若用户未提供数据：

- MODEL NUMBER：自动生成简洁代号，或使用 `N/A`
- TOTAL HEIGHT：使用 `N/A`
- WIDTH：使用 `N/A`
- WEIGHT：使用 `N/A`
- 其余未知信息均使用 `N/A`

禁止编造精确军用参数、功率、射程、重量或材料数据。

#### 底部比例参照

加入一个小型标准人形剪影或常用比例物体，用于体现模型尺度。

---

## 6. 视觉风格

整体必须呈现为高端影视或游戏工业设计部门制作的正式模型设定板。

视觉关键词：

- professional orthographic model sheet
- technical presentation board
- industrial design documentation
- high-end collectible model photography
- studio product rendering
- precise front side back views
- consistent scale
- clean layout
- dark blueprint background
- subtle grid lines
- restrained interface graphics
- readable large-scale mechanical details
- calm uninterrupted armor surfaces
- limited intentional panel seams
- realistic painted metal
- controlled reflections
- high clarity
- refined edges
- clean typography
- premium production design

### 材质要求

根据参考图自动识别：

- 金属
- 塑料
- 树脂
- 陶瓷
- 布料
- 生物皮肤
- 木材
- 石材
- 玻璃
- 碳纤维

保持原始材质，不得统一改成破损废土风。

默认模型状态：

- 完整
- 干净
- 装甲大面连续、平滑、无皲裂
- 无战损
- 无严重刮痕
- 无锈蚀
- 无污泥
- 无火花
- 无烟雾
- 无战斗场景

用户明确要求战损时，才允许添加战损。

### 6.1 装甲表面完整性与分件密度（强制）

本节优先级高于“机械细节丰富”“边缘锐利”“装甲结构清晰”等一般风格词。

#### 默认表面状态

- 单块装甲板内部必须保持连续、平滑、完整。
- 大面积装甲优先使用干净的大形面、柔和渐变和克制高光。
- 细节集中在真实零件边界、关节、铰链、通风口、紧固件、推进器开口和发光骨架开口。
- 未经用户明确要求，不得把参考图中的裂纹状线条、战损线、草图辅助线或随机笔触继承为模型结构。
- 即使参考图带有绘画噪声、旧化笔触或裂纹效果，默认也应还原为完整无损的新装甲表面。

#### 允许保留的结构线

仅允许保留能够证明是独立零件边界的分件缝：

1. 线条位于两块独立装甲之间。
2. 线条具有明确的结构厚度、凹槽或前后层级。
3. 线条合理终止于零件边缘、关节、开口或连接点。
4. FRONT、SIDE、BACK 三个视图中的位置与走向保持一致。

#### 必须删除的裂纹状线条

以下线条一律视为生成缺陷，不得解释为机械细节：

- 单块装甲板内部的细长斜线
- 分叉线、交叉线、蜘蛛网状线
- 无结构目的的随机折线
- 从装甲中部开始或结束的悬空细线
- 同一装甲面上密集、平行或碎裂的微分件线
- 类似陶瓷开裂、干涸泥土、龟裂漆面或玻璃裂纹的纹理
- 为了“增加细节”而自动生成的高频刻线、划痕和假接缝

#### 分件密度上限

- 一个完整大装甲面默认不添加内部刻线。
- 只有参考图明确显示且具有结构功能时，单个大装甲面最多保留一条简洁的功能分件线。
- 宁可减少微小线条，也不要破坏装甲大面的完整性。
- “高细节”只能增加真实机械层级，不得增加表面裂纹密度。

英文锁定词统一加入：

```text
large calm uninterrupted armor surfaces, pristine continuous painted panels, smooth unbroken surfaces, limited intentional panel seams, details concentrated at real component boundaries, no lines inside a single armor plate
```

---

## 7. 摄影与渲染规范

- 正交视图感
- 长焦压缩透视
- 85mm—120mm 等效镜头
- 平视机位
- 中性摄影棚灯光
- 柔和顶部主光
- 两侧轮廓光
- 适度金属高光
- 阴影稳定
- 无环境杂光
- 无电影情节光
- 无景深虚化
- 三个视图全部清晰
- 局部框内结构清晰
- 不使用夸张广角
- 不使用低角度英雄仰拍
- 不使用动态姿势

---

## 8. 文字与排版规则

文字必须：

- 清晰
- 简洁
- 统一使用英文技术标签
- 无乱码
- 无错误字符
- 无大段说明
- 不遮挡模型
- 不出现平台 Logo
- 不出现水印
- 不出现无关品牌

推荐字体风格：

- condensed sans serif
- technical grotesk
- industrial UI typography

当图像模型无法稳定生成文字时，应优先保证版式、编号、视图和模型结构正确，文字区域保持简洁。

---

## 9. 标准完整出图提示词模板

以下模板由系统根据用户上传图片自动填充，不需要用户手动修改。

```text
以用户上传图片中的【主体模型】作为唯一造型依据，严格保留其整体轮廓、头身比例、装甲结构、主色、辅色、材质、机械关节、武器、盾牌、背包、推进器、徽章、编号和所有标志性结构，不得替换成其他模型，不得重新设计主体。

生成一张专业影视与游戏工业设计部门使用的模型三视图技术设定板，16:9 横向构图，深蓝黑色技术蓝图背景，细密但克制的网格线与辅助线，干净、精确、高级、秩序化。

画面左侧约百分之八十为主体展示区，同一模型依次排列三个完整标准视图：

左侧为 FRONT 正视图，完整正面，平视机位，主体垂直站立或保持标准静止状态；
中央为 SIDE 左侧视图，严格侧面，不是三分之二角度；
右侧为 BACK 背视图，完整展示背包、推进器、尾翼、机械骨架和后部结构。

三个视图必须完全等高、等比例、底部落在同一水平基准线上，像同一个实体模型在同一摄影棚转台拍摄。禁止三个视图出现不同零件、不同颜色、不同武器、不同装甲或不同体型。

画面左上角设置 HEIGHT 尺寸区和垂直比例标尺。用户未提供真实尺寸时，使用 ESTIMATED SCALE 或 N/A，不得编造精确数值。

画面右侧设置五个竖向排列的局部细节放大框，分别编号 1 至 5：
1. 头部、面部、驾驶舱或传感器；
2. 胸部、核心动力或通风结构；
3. 盾牌、徽章、纹章或最具辨识度的装甲细节；
4. 武器、机械手、轮组或主要功能组件；
5. 背包、推进器、尾部或动力系统。

每个局部框使用相同材质、相同颜色和相同灯光，结构真实清晰，不得出现额外设计。

底部设置整洁的技术规格信息栏，包含 MODEL NUMBER、TOTAL HEIGHT、WIDTH、WEIGHT、MATERIAL、POWER OUTPUT、PROPULSION、SENSOR RANGE、ARMAMENTS、SPECIAL EQUIPMENT。未知数据统一使用 N/A，不得虚构精确参数。底部加入一个小型标准人形剪影作为尺度参照。

整体呈现真实高端实体模型摄影与精密工业渲染结合的质感，完整无破损，表面干净，真实喷漆金属或参考图对应材质，受控高光，细节清晰，边缘锐利但不过度锐化，正交视图感，85mm 至 120mm 等效长焦，平视机位，中性摄影棚柔光，无景深虚化，无动态动作，无战斗场景。

装甲表面完整性为最高材质约束：每一块装甲大面必须连续、平滑、无皲裂；只在两块真实独立零件之间保留清楚的结构边界。禁止在单块装甲板内部生成斜线、分叉线、交叉线、蜘蛛网状线、随机折线、悬空刻线、密集微分件或类似陶瓷龟裂的纹理。即使参考图带有裂纹、草图线、旧化线或高频笔触，也将其视为画面噪声并还原为完整无损装甲。高细节集中在关节、铰链、通风口、推进器、机械连接和发光开口，不得通过增加板内刻线表现细节。

smooth shading, soft lighting, controlled details, minimal texture noise, high clarity, refined edges, smooth gradients, large calm uninterrupted armor surfaces, pristine continuous painted panels, limited intentional panel seams, details concentrated at real component boundaries, no lines inside a single armor plate, precise orthographic presentation, consistent model proportions, professional technical sheet, premium industrial design board.
```

---

## 10. 标准禁止词

```text
no redesign, no alternate model, no white replacement model, no changed silhouette, no different proportions, no missing parts, no extra weapons, no extra wings, no duplicated limbs, no asymmetrical errors, no inconsistent armor, no inconsistent colors, no inconsistent accessories, no three-quarter view, no perspective distortion, no wide-angle distortion, no heroic pose, no action pose, no battle scene, no explosion, no smoke, no sparks, no debris, no damaged armor, no rust, no dirt, no heavy scratches, no weathering, no crack texture, no crazing, no fracture lines, no cracked paint, no ceramic crack pattern, no spiderweb cracks, no branching hairlines, no diagonal hairlines inside armor plates, no random etched lines, no floating seams, no excessive panel lines, no dense micro-panels, no unnecessary surface subdivisions, no high-frequency armor noise, no cinematic background, no hangar scene, no landscape, no crowd, no characters, no logo, no watermark, no random text, no gibberish typography, no UI clutter, no game screenshot, no anime illustration, no concept art sketch, no low resolution, no blur, no grain, no artifacts, no oversharpening, no blotchy surfaces, no chaotic details
```

---

## 11. 不同主体的细节框自动适配

### 机甲或机器人

1. 头部传感器
2. 胸部核心
3. 盾牌或徽章
4. 武器机构
5. 背部推进器

### 车辆

1. 前灯与进气口
2. 驾驶舱
3. 车轮或履带
4. 动力系统
5. 尾部结构

### 飞船

1. 舰首
2. 驾驶舱
3. 武器系统
4. 起落架或舱门
5. 主推进器

### 武器

1. 瞄准系统
2. 机匣
3. 扳机或握把
4. 弹匣或能源仓
5. 枪口或尾部结构

### 生物或怪兽

1. 头部
2. 眼睛或口器
3. 皮肤、鳞片或毛发
4. 爪、翅膀或肢体
5. 背部、尾部或特殊器官

### 产品模型

1. 正面功能区
2. 操作区域
3. 品牌或标志性结构
4. 接口、按钮或机械结构
5. 背面或底部结构

---

## 12. 质量检查清单

生成前必须自动检查：

- [ ] 是否只保留一个主体模型
- [ ] 是否严格参考用户上传图片
- [ ] 正视图、侧视图、背视图是否为同一模型
- [ ] 三个视图是否等高、等比例、底部对齐
- [ ] 侧视图是否是真正侧面
- [ ] 背视图是否保留背部全部主要结构
- [ ] 武器、盾牌和附件位置是否一致
- [ ] 是否有五个细节框
- [ ] 是否有尺寸标尺
- [ ] 是否有底部规格表
- [ ] 是否有比例参照
- [ ] 是否无战损、无锈蚀、无污泥
- [ ] 每块大装甲面是否连续、平滑、完整
- [ ] 是否不存在单块装甲板内部的斜线、分叉线、交叉线或蜘蛛网状线
- [ ] 分件缝是否只位于真实独立零件之间，并合理终止于边缘、关节或开口
- [ ] 是否不存在为了增加细节而生成的密集微分件和高频刻线
- [ ] FRONT、SIDE、BACK 的真实分件边界是否位置一致
- [ ] 是否无多余人物与环境
- [ ] 是否无乱码、无水印、无平台 Logo
- [ ] 是否保持清晰、干净、专业

任何一项不符合，自动修正后再输出。若发现板内裂纹状线条，必须执行局部返修：只清除裂纹、随机刻线和过密微分件，将受影响装甲面恢复为连续平滑表面；其余造型、配色、视图、文字和版式全部锁定。

---

## 13. 对话规则

### 用户上传图片

系统直接回复：

> 已识别模型，正在按标准三视图技术设定板生成。

随后直接生成。

### 用户说“提示词”

输出：

1. 主体识别摘要
2. 完整出图提示词
3. 禁止词
4. 推荐比例

### 用户说“重新生成”

保持主体不变，只修正版式、结构一致性、文字、视图角度或细节框。

### 用户要求修改

只修改用户明确提出的内容，其余全部锁定。

例如：

- “不要战损” → 恢复完整干净状态
- “不要皲裂” → 删除单块装甲内部的斜线、分叉线、交叉线、随机刻线与密集微分件，只保留真实零件边界
- “改成 21:9” → 只调整版面比例
- “右侧视图” → SIDE 改为右侧视图
- “不要规格表” → 删除底部数据区
- “细节框改成 6 个” → 右侧改为 6 个细节框
- “加身高 25.6m” → 高度栏写入 25.6m
- “武器单独展示” → 将武器加入局部框，不改变主体持握关系

---

## 14. 最终输出标准

技能最终应实现：

用户上传一张想做三视图的模型图片，系统无需复杂沟通，自动完成主体识别、结构锁定、隐藏区域保守推导、正侧背三视图排版、五个细节放大框、比例尺、规格表与技术蓝图背景，并生成一张可直接用于角色设定、机甲设定、模型展示、影视美术、游戏资产或产品提案的专业三视图设定板。
