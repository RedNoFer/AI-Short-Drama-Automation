---
name: zhifeiji-illustration-to-photoreal-character
description: 将人物、异形或科幻角色插画通过纯黑白线稿、可选脸型与眼型调整、9:16正面肖像开发与强制锁脸门控、结构与配色参考、皮肤和材质增强流程，转换为保持角色身份与视线的影视级高写实脸部封面、正面全身人物资产图，或锁脸后输出“左侧最终脸部特写＋右侧正面/侧面/背面”的16:9人物三视图设定板。未锁脸时必须先生成正面头肩肖像，禁止执行全身和三视图。用于“转线稿”“先定脸”“生成正面肖像”“调整五官”“锁定这张脸”“人物三视图”“转高写实人物资产”“提升皮肤质感”等请求。
---

# ZHIFEIJI｜插画转高写实人物资产 SKILL v1.5

版本标识：v1.5

## 1. SKILL 定位

将用户上传的人物、卡通角色、异形生物、机械人体或科幻角色插画转换为两类互相衔接的资产：

- 9:16 严格正面脸部定妆母版：先确认脸型、五官、眼神、皮肤与面部材质。
- 9:16 完整正面全身人物资产：继承已确认的脸部身份、全身结构、服装和配色。
- 16:9 人物身份三视图设定板：左侧为正面脸部特写，右侧为同一人物的正面、侧面、背面全身视图。
- 两类资产均为单一角色、正视角和影视级高写实质感。
- 保持原插画身份、比例、服装和配色
- 具有真人摄影可信度的电影级材质；不得停留在干净的通用 3D 角色渲染质感
- 皮肤、毛发、布料、金属和机械件材质分离清楚

单张脸部与单张全身模式只输出正视角；只有用户明确要求“人物三视图”时，才生成侧视图、背视图和横向设定板。
本 SKILL 同时用于创建原创 AI 人物：先从插画提取结构线稿，再按用户选择调整脸型和眼型；确认后的最终线稿定义为“角色身份母版线稿”，后续所有写实化、换服装和换场景任务都以它锁定人物身份。
在全身写实化前，必须生成并确认“脸部定妆母版”；确认后的脸部母版是后续所有高写实输出的最高优先级面部身份参考。未执行“锁定这张脸”时，全身与三视图处于锁定状态。

---

## 2. 核心原则

### 2.1 写实化不是重设计

严格保持：

- 头身比例
- 脸型和下巴轮廓；只有用户明确启用“调整脸型”时才允许局部修改
- 五官相对位置
- 眼睑形状；只有用户明确启用“调整眼型”时才允许局部修改
- 瞳孔大小与视线方向
- 原始表情和情绪
- 发型轮廓、分缝、卷曲方向和发色
- 身材、年龄感和物种特征
- 服装剪裁、层级、图案和颜色
- 配饰、道具、机械件和生物附属物

禁止为了“更像真人”擅自改成普通真人比例、标准网红脸或时尚模特脸。
若原角色是大头、短肢、低眼睑、斜视、无精打采或夸张卡通比例，必须保留这些身份特征，只升级材质和光影。
脸型与眼型调整是两项可选例外：脸型只修改面部外轮廓；眼型只修改眼裂与眼睑轮廓。不得借机换脸、美化五官或改变人物身份。用户未明确指定时，始终保持原脸型和原眼型。

### 2.2 两张参考图职责分离

转换阶段固定使用：

- Image Prompt 1：纯黑白线稿，负责结构、比例、轮廓、姿态和五官位置。
- Image Prompt 2：原始彩色插画，负责颜色、材质分区、图案、标识和情绪。

结构冲突时优先 Image Prompt 1。

颜色冲突时优先 Image Prompt 2。

禁止用彩色图重新设计结构，禁止用线稿猜测新配色。

若执行过脸型或眼型调整，Image Prompt 1 必须使用调整后的最终线稿；原始彩色插画仍只负责配色与材质分区。

### 2.3 正面资产优先

全身资产模式默认输出：

- 单人
- 正面中立站姿
- 头部和身体朝向镜头
- 双臂自然下垂或按原设定保持对称
- 双脚完整可见
- 头顶、手部和脚部不裁切
- 70mm—105mm 等效镜头
- 平视机位
- 无广角畸变
- 9:16 竖构图
- 中性浅灰、暖灰或低对比影棚背景

若原图不是正面，保留身份与服装，用保守方式推导被遮挡结构，不增加新设计。

脸部定妆母版模式默认输出：

- 单人，严格正面，头部不偏转、不俯仰
- 头肩至上胸构图，不输出全身
- 眼睛接近画面上方三分之一，脸部占画面高度约 45%—60%
- 平视机位，85mm—135mm 等效人像镜头
- 9:16 竖构图
- 表情保持原设定；原图无明确表情时使用克制中性表情
- 纯白无缝影棚背景，背景独立打亮但不得把白光溢到脸部边缘
- 影视定妆照或角色海报封面质感，不是行政证件照质感

“类似证件照”只表示严格正面、身份清楚、五官无遮挡；不得解释为白底、平光、闪光灯直打、磨皮或廉价证件照排版。

### 2.4 强制肖像锁脸门控（v1.5）

本 SKILL 必须根据当前对话和已上传参考图判断状态，不得在一个菜单里同时开放所有阶段。

最高优先级短规则：必须先生成肖像并锁脸。未锁脸时禁止全身，禁止三视图。

#### 状态 A｜尚未锁脸

符合任一情况即视为“尚未锁脸”：

- 当前对话没有明确执行过“锁定这张脸”。
- 没有已确认的 9:16 严格正面脸部定妆母版。
- 只有原始插画或线稿，没有可作为 Image Prompt 3 的脸部母版。

此状态下：

- 默认下一步是生成 9:16 严格正面、头肩至上胸的影视肖像照。
- 允许先生成纯线稿或调整脸型、眼型和五官。
- 禁止生成正面全身。
- 禁止生成人物三视图。
- 禁止把“9:16”“正面”“转高写实人物资产”解释为完整全身。
- 用户输入旧数字“4”、旧命令“转全身”或“正面9:16全身”时，不得执行全身；必须拦截并返回先定脸流程。
- 用户输入旧数字“5”或“三视图”时，不得执行三视图；必须拦截并返回先定脸流程。

网页兼容短规则：

- 未锁脸时回复旧数字“4”，不得生成全身，必须自动返回正面肖像流程。
- 未锁脸时回复旧数字“5”，不得生成三视图，必须自动返回正面肖像流程。

网页端首次收到图片时必须显示以下阶段菜单，不得提前显示全身与三视图选项：

```text
当前阶段：脸部身份开发（尚未锁脸）

1｜生成纯黑白身份线稿
2｜生成9:16严格正面肖像照（默认）
3｜调整脸型、眼型或五官

全身与三视图尚未解锁。请先生成肖像并回复“锁定这张脸”。
```

若用户没有选择数字，只说“开始”“转高写实”“按Skill执行”或上传图片后要求直接处理，默认自动执行选项 2。

选项 2 的首要构图锁必须位于提示词最前方：

```text
PORTRAIT FIRST. Create one single 9:16 strict-front head-and-shoulders to upper-chest
live-action cinematic character portrait. This is a face identity look-development master,
NOT a full-body image. Do not show the waist, legs or feet.
```

若用户只上传一张原图，允许直接先定脸：

- 该图同时负责身份、脸型、五官、视线、发型、颜色、服装领口和面部材质分区。
- 不得因缺少线稿而跳到全身。
- 若用户随后需要精确调整结构，再生成线稿并返回脸部开发阶段。

#### 状态 B｜肖像已生成但尚未确认

必须显示：

```text
当前阶段：脸部定妆确认

1｜调整脸型或五官
2｜重新生成正面肖像
3｜锁定这张脸

全身与三视图仍未解锁。
```

此状态下所有调整仍只输出 9:16 正面肖像，不得输出全身或三视图。

#### 状态 C｜已锁定脸部母版

仅当用户明确说出“锁定这张脸”“确认这张脸”或“脸部母版确认”后，才进入此状态并显示：

```text
当前阶段：脸部母版已锁定

1｜生成9:16正面全身
2｜生成人物三视图
3｜继续提升皮肤和材质
4｜返回调整脸部
```

状态 C 中：

- 正面全身必须使用已锁定脸部母版作为 Image Prompt 3。
- 人物三视图必须使用已锁定脸部母版作为最高优先级面部参考。
- 若用户返回调整脸部，立即撤销全身与三视图解锁，直到再次锁脸。

---

## 3. 三阶段标准流程

### 阶段一｜原插画转纯黑白线稿

目标：把复杂插画拆成稳定、可复用的结构控制图。

执行要求：

- 只保留纯黑和纯白
- 不保留灰阶
- 不保留颜色
- 不保留渐变
- 不保留阴影、反光、材质噪声和背景
- 保留完整外轮廓
- 保留五官、眼神、发型、服装分区、手部和配饰
- 线条干净、流畅、闭合、粗细稳定
- 禁止增加装饰线和无依据结构

正面资产模式下，将角色整理为正视角中立站姿线稿。若原图遮挡严重，只保守补全必要结构。

#### 阶段一标准命令

```text
把原图中的角色转换为干净、流畅、准确的正视角纯线稿，只保留黑白两色。
严格保持原角色的头身比例、脸型、五官位置、眼睑形状、瞳孔方向、表情、发型轮廓、服装剪裁、配饰、道具和整体造型。
角色采用正面中立站姿，完整全身，头顶、双手和双脚全部可见，9:16竖构图。
去除背景、色彩、灰阶、渐变、阴影、反光、纹理、噪声和多余杂线。
线条清楚、连续、闭合、粗细稳定；黑白层次明确，不增加新部件，不改变眼神，不改成普通真人比例。
```

#### 阶段一负面约束

```text
不要颜色，不要灰阶，不要渐变，不要阴影，不要材质，不要背景，不要速写脏线，不要重复线，不要断线，不要涂抹，不要改变脸型，不要改变眼神，不要改变发型，不要改变服装，不要改变比例，不要多余手指，不要裁切头部和脚部，不要侧面，不要三分之二视角，不要三视图，不要文字，不要Logo，不要水印。
```

---

### 阶段一B｜纯线稿脸型与眼型调整（可选）

仅在线稿完成后、写实填色前执行。脸型可选：

- 鹅蛋脸：额头略宽于下颌，面颊平顺，下巴柔和收窄。
- 菱形脸：颧骨最宽，额头与下颌较窄，下巴清晰。
- 圆脸：脸长接近脸宽，面颊饱满，下颌角柔和。
- 倒三角脸：额头较宽，下半脸逐渐收窄，下巴较尖但自然。
- 长脸：纵向比例增加，脸宽克制，下巴不过尖。
- 方脸：额头、颧骨与下颌宽度接近，下颌角更明确。

眼型可选：

- 三角眼：外眼角略下垂，外侧上眼睑覆盖更明显，眼裂趋近三角形。
- 桃花眼：眼裂偏长，上眼睑弧度较大，内眼角略收，眼尾柔和弯曲。
- 狐狸眼：内眼角略低、外眼角上扬，眼裂狭长锐利。
- 瑞凤眼：眼裂细长，上下眼睑纤细，虹膜自然被眼睑部分覆盖。
- 肿泡眼：上眼睑体积较饱满、折叠较厚，眼裂相对收窄但不表现病态。

脸型和眼型可单独或同时调整，默认“轻度”。未指定的项目保持原样。

#### 脸型与眼型调整命令

```text
以当前纯黑白线稿为唯一结构基础，把脸型调整为【不调整/脸型类型】，把眼型调整为【不调整/眼型类型】，强度为【轻度/中度】。
脸型只允许修改额头宽度、颧骨宽度、面颊弧线、下颌角和下巴长度；眼型只允许修改上下眼睑弧度、内外眼角走向和眼裂长宽比例。
严格锁定双眼间距、虹膜与瞳孔大小、瞳孔位置、视线方向、眉毛、鼻子、嘴巴、耳朵、表情、年龄、发际线、发型、头部朝向、头身比例、身体、服装和配饰。
继续保持纯黑白两色、干净闭合线条、正视角完整全身和9:16竖构图，不填色，不写实化。
```

#### 脸型与眼型调整负面约束

```text
不要换脸，不要网红脸，不要美容整形感，不要改变双眼间距、虹膜、瞳孔和视线方向，不要改变眉鼻嘴和表情，不要改变年龄和性别特征，不要改变头围和头身比例，不要改变发型和身体，不要左右眼错位，不要斗鸡眼，不要填色，不要灰阶，不要阴影，不要写实皮肤。
```

调整后必须先检查人物是否仍可被认出；若身份相似度下降，降低强度或恢复原脸型、原眼型。

用户确认后，将结果标记为“角色身份母版线稿”。同一角色后续不得随机改变脸型、眼型、五官间距、瞳孔、视线和头身比例；需要改变时必须重新得到用户明确指令。

---

### 阶段一C｜9:16 正面脸部定妆母版

目标：在生成全身资产前，用足够大的面部像素先锁定脸型、五官、眼神、皮肤、毛发边缘和面部机械/生物材质。此阶段输出的是单张影视级正面角色封面，不是全身图，也不是多图拼版。

输入职责：

- Image Prompt 1：最终角色身份母版线稿，负责脸型、五官位置、眼睑、瞳孔、视线、头部附属物和正面朝向。
- Image Prompt 2：原始彩色插画，负责肤色、发色、配色、面部材质分区、标记和原始情绪。

单图直接先定脸模式：

- 用户只上传一张原始图片时，不等待第二张图；将它同时作为身份、结构、颜色和面部材质参考。
- 直接生成本阶段的 9:16 正面头肩肖像，不得输出全身。
- 后续若补充最终线稿，则以线稿覆盖结构职责，原图继续负责颜色。

#### 脸部摄影媒介锁定

人类或类人角色统一使用：

```text
A live-action cinematic character publicity portrait with photographic facial realism, captured as a premium feature-film key-art cover. Real optical depth, physically plausible skin translucency, restrained color grading, natural highlight roll-off, and authentic on-set portrait texture. Not a CGI render, not a digital maquette, not a beauty advertisement.
```

异形、生物或机械角色将“真人皮肤”替换为对应材质，并使用：

```text
A live-action cinematic creature or robotic character publicity portrait with feature-film practical-effects, prosthetic-makeup, animatronic or hero-prop material credibility. Photographic lighting and optical depth; not a game asset preview, not a toy, not a clean generic CGI render.
```

#### 相机、曝光与影棚锁定

单脸开发稿统一使用：

```text
Hasselblad H6D medium-format photographic look, 100mm-class medium-format portrait lens, f/2.8, ISO 50, maximum clean dynamic range, smooth medium-format tonal transitions, natural highlight roll-off, 8K-resolved facial detail and IMAX-scale live-action skin fidelity.

Professional three-point studio lighting: a soft key light 35 to 45 degrees off-axis, a controlled fill light 1.5 to 2 stops below the key, and a restrained rim or separation light. Pure white seamless cyclorama background, independently lit to clean white without clipping the character silhouette or spilling flat light across the face.

At f/2.8, keep both irises, eyelids, nose, lips and the primary facial plane in critical focus. Allow only gentle optical falloff behind the ears, rear hair and shoulders; never blur identity-defining facial features.
```

“IMAX级真实皮肤纹理”必须落实为真实尺度毛孔、细皮纹、绒毛、毛囊、次表面散射、自然不均匀红润、低频肤色变化与受光微对比；不得解释为全脸均匀锐化、粗大毛孔、数字噪声或磨皮后叠加纹理。

#### 脸部定妆母版完整提示词

```text
PORTRAIT FIRST. Create one single 9:16 vertical, strict-front, head-and-shoulders to upper-chest live-action cinematic character portrait. This is a face identity look-development master, NOT a full-body image. Do not show the waist, legs or feet.

When two references are available, use Image Prompt 1 as the authority for face contour, facial placement, eyelid shape, pupil position, gaze, expression, hairstyle silhouette and head attachments. Use Image Prompt 2 as the authority for color, markings and material assignment. When only one original image is supplied, use it as the combined authority for identity, facial structure, gaze, hairstyle, color and facial material assignment. Do not redesign, beautify, normalize or replace the identity.

Hasselblad H6D medium-format photographic look, 100mm-class medium-format portrait lens, f/2.8, ISO 50, maximum clean dynamic range, smooth tonal transitions, natural highlight roll-off, 8K-resolved detail and IMAX-scale live-action skin fidelity. Eye-level camera, no wide-angle distortion, no head turn, no tilt, no three-quarter angle. Show the complete top of the head, both sides of the face where the design permits, the neck, shoulders and upper chest. The face occupies roughly 45% to 60% of the image height. Preserve the original expression and gaze.

For visible human skin, show scale-accurate visible pores, fine skin lines, tiny vellus hair, subtle follicle detail, physically plausible subsurface scattering, and natural non-uniform red and warm coloration around the cheeks, nose, ears, eyelids and lips. Preserve low-frequency tonal variation across the face. Skin must feel hydrated and alive, not oily. Retain natural asymmetry and age-appropriate micro-detail.

Use professional three-point studio lighting: a soft 35-to-45-degree key light, a controlled fill 1.5 to 2 stops below the key, and a restrained rim or separation light. Use a pure white seamless cyclorama background independently lit to clean white without clipping the silhouette or washing flat light across the face. Keep readable transitions in the eye sockets, nose wings, philtrum, lips, chin, jaw and neck. Add subtle organic filmic micro-contrast and fine luminance grain carried by light and skin response, not dirt or synthetic noise. Keep the production clean but never sterile, airbrushed, textureless or flat.

At f/2.8, keep both irises, eyelids, nose, lips and the primary facial plane critically sharp. Restrict gentle optical focus falloff to the rear hair, ears and shoulders; identity-defining features must never blur.

Render hair as grouped natural fibers with fine flyaways only where plausible. Separate skin, hair, cloth, leather, painted metal, bare metal, glass, rubber and biological tissue through physically credible roughness, translucency and reflection. Preserve controlled imperfections that describe construction and use; do not add random cracks, grime or decorative damage.
```

#### 脸部定妆母版负面约束

```text
no changed identity, no changed face shape, no changed facial spacing, no changed eyelids, no changed pupils, no changed gaze, no changed expression, no beautified influencer face, no beauty retouching, no makeup-ad skin, no wax skin, no plastic skin, no silicone mannequin, no porcelain face, no airbrushed skin, no sterile over-clean skin, no textureless smooth gradients, no uniform pore overlay, no oversized pores, no wrinkle filter, no dirt-as-detail, no grunge overlay, no random freckles, no acne added without reference, no flat frontal lighting, no ring-light look, no uniform fill, no passport-booth flash, no high-key flat wash, no white background spill on skin, no clipped white silhouette edges, no blurred eyes, no blurred nose, no blurred lips, no crushed shadows, no orange-and-teal color cast, no excessive sharpening, no coarse digital noise, no CGI render look, no game-character preview, no digital maquette, no toy, no figurine, no full body, no side view, no three-quarter view, no collage, no text, no logo, no watermark, no UI
```

生成后必须先检查脸部身份、眼神、皮肤与面部材质。此时结果只是“单脸开发稿”，允许继续执行阶段一D逐项调整五官。用户确认“锁定这张脸”后，才将结果标记为“脸部定妆母版”。未确认前不得自动进入全身高写实或人物三视图阶段。

---

### 阶段一D｜单脸五官局部调整

只对当前 9:16 单脸开发稿执行。用户可以用自然语言指定调整：

- 脸部外轮廓：额头、颧骨、面颊、下颌角、下巴。
- 眉毛：眉形、粗细、眉峰、眉尾走向和高度。
- 眼睛：眼裂长宽、眼睑弧度、内外眼角和眼皮厚度。
- 鼻子：鼻梁宽度与高度、鼻尖、鼻翼和鼻孔形态。
- 嘴与嘴唇：嘴宽、唇峰、上下唇厚度、嘴角状态。
- 耳朵：大小、轮廓、贴耳程度和高度。

每次只修改用户明确指定的部位；未指定部位全部锁定。调整眼型时继续锁定虹膜、瞳孔、双眼间距和视线，除非用户明确要求改变其中某项。调整五官不得连带改变年龄、物种、性别特征、头部朝向、表情、发型、服装、肤色、面部材质、灯光、背景和 9:16 构图。

#### 五官局部调整命令

```text
只调整当前单脸开发稿的【指定五官与具体要求】，调整强度为【轻度/中度】。
仅允许修改与该五官直接相关的形状和局部比例；脸部其余所有区域逐像锁定。严格保持人物身份、其他五官、双眼间距、虹膜、瞳孔、视线、表情、年龄、物种、头部朝向、发型、服装、肤色、皮肤与材质质感、灯光、背景和9:16构图不变。
调整后继续输出严格正面的单张头肩脸部开发稿，不输出全身，不输出三视图。
```

#### 五官局部调整负面约束

```text
no full-face redesign, no identity drift, no beautified influencer face, no change to unspecified facial features, no changed gaze unless explicitly requested, no changed expression, no changed age, no changed species, no changed hairstyle, no changed costume, no skin smoothing, no changed lighting, no changed background, no full body, no side view, no three-view sheet
```

每次调整后继续由用户检查。只有用户明确说“锁定这张脸”，才能结束单脸开发并进入全身或人物三视图输出。

---

### 阶段二｜线稿锁结构、原图锁颜色的高写实转换

目标：保留插画设计，升级为具有真人摄影可信度的高写实电影级角色资产。

#### 强制前置条件

阶段二只有在“状态 C｜已锁定脸部母版”时允许执行。

- Image Prompt 3 必须存在，并且必须是用户已确认的 9:16 正面脸部定妆母版。
- 若 Image Prompt 3 不存在，不得生成全身，不得用原图中的小脸直接推导全身身份。
- 用户输入“4”“转全身”“图1根据图2转全身”“正面9:16全身”或“转高写实人物资产”时，只要尚未锁脸，统一返回：

```text
当前尚未锁定脸部母版，正面全身暂未解锁。
现在先生成一张9:16严格正面、头肩至上胸的影视肖像照。
肖像确认后请回复“锁定这张脸”，再执行全身。
```

#### 媒介锁定

统一使用：

```text
A premium feature-film character asset with live-action photographic credibility, physically based materials, realistic material separation, restrained cinematic color and believable practical construction. Preserve production-ready design fidelity without a toy, figurine, game-preview, digital-maquette or clean generic CGI-render aesthetic.
```

“收藏级”只表示制作精度，不得生成小比例玩具、底座、包装盒或塑料手办感。

#### 双参考锁定

统一加入：

```text
Perfectly replicate the complete structure, silhouette, proportions, final face contour, facial placement, final eyelid and eye-fissure shape, gaze direction, hairstyle, outfit construction, accessories and pose strictly based on Image Prompt 1, the final clean black-and-white line art, including only explicitly approved face-shape and eye-shape adjustments.
Apply the original color palette, color blocking, patterns, markings and material assignments strictly based on Image Prompt 2, the original color illustration.
Do not redesign, beautify, normalize or replace the character identity.
```

必须增加 Image Prompt 3：

- Image Prompt 3：已确认的脸部定妆母版，只负责脸部身份、五官微细节、眼神、肤色/面部材质和面部真实度。
- Image Prompt 3 必须使用已确认的脸部定妆母版；缺少或未确认时立即停止全身生成。
- 脸部发生冲突时，Image Prompt 3 的优先级高于 Image Prompt 1 和 Image Prompt 2。
- Image Prompt 3 不得改变身体比例、服装、姿态、全身配色或新增配饰。

#### 正面人物资产锁定

统一加入：

```text
Single character, strict front view, neutral standing pose, full body visible from head to feet, eye-level camera, 70mm to 105mm portrait lens, no perspective exaggeration, centered 9:16 vertical character asset presentation, clean neutral studio background.
```

---

### 阶段二A｜脸部特写＋人物三视图设定板（可选）

用户明确说“人物三视图”“生成脸部特写＋人物三视图”或“图1根据图2进行提示词修正：人物三视图”时执行。此模式输出单张 16:9 横向人物身份设定板，不输出技术规格表、尺寸标尺、细节框、文字标签或 UI。

参考职责：

- Image Prompt 1：最终纯黑白线稿，锁定头身比例、结构、轮廓、五官位置和服装造型。
- Image Prompt 2：原始彩色插画，锁定颜色、材质分区、图案、标记与情绪。
- Image Prompt 3：已确认脸部定妆母版，必须存在，并以最高优先级锁定脸部身份、眼神、肤色/面部材质和面部微细节。

若尚未执行“锁定这张脸”，不得生成人物三视图。先返回阶段一C生成单脸开发稿，允许用户按阶段一D调整五官，直到用户明确确认锁脸。

#### 版式与视图

- 16:9 横向画布，纯白无缝影棚背景；背景独立打亮，人物轮廓不得过曝或融入白底。
- 左侧约 38%—42%：严格正面头肩至上胸特写，完整保留头顶、脸部两侧、颈部和肩部。
- 右侧约 58%—62%：从左至右排列 FRONT 正视图、SIDE 左侧视图、BACK 背视图。
- 三个全身视图必须等高、等比例、底部对齐，均完整显示头顶、双手与双脚。
- FRONT 与 BACK 使用严格正交方向；SIDE 必须为 90 度纯侧面，不得变成三分之二视角。
- 三视图采用相同中立站姿、相同体型、相同服装、相同材质、相同配色、相同配饰与相同装备。
- 隐藏区域只允许依据线稿、原图可见连接关系与对称逻辑保守补全；不确定处宁可简化，不得增加新设计。

#### 完整提示词

```text
Create one clean 16:9 horizontal cinematic character identity sheet from the references on a pure white seamless studio cyclorama. Light the background independently to clean white without clipping or dissolving the character edges. The left 38% to 42% is a large strict-front head-and-shoulders look-development portrait. The right 58% to 62% contains three equal-height, equal-scale, baseline-aligned full-body orthographic views of the same character: FRONT, exact 90-degree left SIDE, and BACK. No labels, no captions, no measurements, no detail boxes, no borders and no interface graphics.

Use Image Prompt 1 as the authority for silhouette, proportions, facial placement, hairstyle, outfit construction, pose and accessories. Use Image Prompt 2 as the authority for color, markings and material assignment. Image Prompt 3 is the required, user-confirmed final face master; use it with highest priority for facial identity, eyelids, pupils, gaze, skin or facial-material response and approved facial micro-detail. Every view must depict one identical character with the same face, head shape, hair, body proportions, costume, colors, materials and equipment.

The large portrait uses a Hasselblad H6D medium-format photographic look, a 100mm-class medium-format portrait lens, f/2.8 and ISO 50, with 8K-resolved detail and IMAX-scale live-action skin fidelity. Use professional three-point lighting: a soft 35-to-45-degree key, controlled fill 1.5 to 2 stops lower, and restrained rim light. Keep both eyes, eyelids, nose, lips and the primary facial plane critically sharp; allow focus falloff only behind the ears, rear hair and shoulders. Retain scale-accurate visible pores and fine skin lines where human skin is present, tiny vellus hair, physically plausible subsurface scattering, natural non-uniform warm and red coloration, low-frequency tonal variation, natural asymmetry, readable shadow transitions and subtle organic filmic micro-contrast. Keep it clean but never sterile, airbrushed, textureless or flat. For alien, creature or mechanical faces, replace human skin detail with physically credible species or machine materials while preserving the same photographic depth and lighting hierarchy.

The three full-body views retain Hasselblad-like medium-format tonal response and ISO 50 cleanliness but use sufficient depth of field for complete orthographic sharpness; f/2.8 shallow-depth blur applies only to the large portrait. Use consistent neutral three-point studio lighting with no depth-of-field blur and no perspective exaggeration on the full-body views. Show the complete head, hands and feet in every view. Preserve practical material separation across skin, hair, cloth, leather, glass, rubber, painted metal, bare metal and biological tissue.
```

#### 禁止词

```text
no different character between panels, no face drift, no changed age, no changed species, no changed hairstyle, no changed body type, no changed costume, no changed colors, no missing accessories, no extra equipment, no asymmetry mistakes, no three-quarter side view, no perspective view, no action pose, no cropped head, no cropped hands, no cropped feet, no duplicate limbs, no portrait-only output, no full-body-only output, no fourth body view, no technical blueprint, no specification table, no measurements, no detail callouts, no text, no labels, no logo, no watermark, no UI, no white replacement costume, no beauty retouching, no wax skin, no plastic skin, no sterile over-clean face, no flat frontal light, no uniform fill, no high-key flat wash, no white background spill, no clipped white silhouette edges, no blurred portrait eyes, no depth-of-field blur on the full-body views, no dirt-as-detail, no coarse noise, no toy, no figurine, no game-character preview, no clean generic CGI-render look
```

参考示例中的白底只作为版式参考，不作为皮肤和平光风格参考。脸部质感仍服从阶段一C，三视图一致性高于局部装饰细节。

---

## 4. 人体皮肤写实规则

只对原图中可见的人类皮肤区域使用：

- 物理可信的皮肤厚度
- 次表面散射 SSS
- 自然毛孔
- 极细皮纹
- 与年龄相符的微小褶皱
- 细小绒毛与毛囊
- 鼻翼、耳朵、脸颊和指尖的自然血色
- 嘴唇和眼周的轻微湿润感
- 冷暖微变化
- 不完全对称的真实微细节

皮肤必须温润、有生命感，但不能油腻、脏污或过度红润。

### 4.1 年龄与物种约束

- 儿童或幼态角色：毛孔细腻，褶皱极少，不得生成成人老化纹。
- 成年角色：保留自然毛孔、眼周和表情区域的轻微细纹。
- 老年角色：按原图年龄增加合理皮肤层次，不夸张衰老。
- 非人类角色：使用符合物种设定的真实皮层、鳞片、软组织或细毛，不强行套用人类皮肤。
- 机械区域：禁止生成毛孔和人类皮肤。

### 4.2 皮肤负面约束

- 不要蜡像皮肤
- 不要塑料皮肤
- 不要硅胶假人
- 不要陶瓷脸
- 不要磨皮
- 不要均匀毛孔贴图
- 不要满脸夸张皱纹
- 不要粉刺堆积
- 不要油亮高光
- 不要过度锐化
- 不要脏污颗粒

---

## 5. 眼神与面部身份锁定

眼神是最高身份特征之一。

必须锁定：

- 上下眼睑开合程度
- 瞳孔在眼白中的位置
- 左右眼视线方向
- 眼球露白比例
- 眉毛高度与角度
- 鼻尖方向
- 嘴角状态
- 原始情绪

禁止自动把斜视改为直视、把半闭眼改成睁大眼、把疲惫表情改成微笑、把不对称眼神改成标准对称眼神。

眼球材质包含湿润角膜、自然高光、虹膜深度和眼睑接触阴影，但不得出现玻璃珠、玩偶眼或过亮发光眼。

---

## 6. 毛发与有机材质

### 6.1 头发

- 保留原发型整体体块
- 保留刘海、分缝、卷度、发旋和蓬松度
- 使用真实发丝束与少量飞丝
- 发丝高光方向服从主光
- 禁止把卷发改直、短发改长或改变发色
- 禁止每根头发同样清晰造成钢丝感

### 6.2 毛皮或绒面生物

猫、动物或有机附属物使用：

- 细密自然毛发
- 明确生长方向
- 柔软绒面层次
- 皮肤与毛发交界自然

禁止光滑塑料动物、橡胶皮或统一绒布贴图。

### 6.3 异形皮肤

参考图库中的异形角色逻辑：

- 细密皮层纹理
- 局部褶皱遵循骨骼与肌肉走向
- 眼周、口鼻和颈部层次可信
- 粗糙度变化克制

禁止把异形皮肤处理成石头裂纹、干涸泥土或均匀噪声。

---

## 7. 服装与机械材质

### 7.1 布料

根据原图判断：

- 棉布：细密织纹、柔和褶皱
- 羊毛或针织：可见纱线结构
- 丝绸：方向性柔和高光
- 皮革：细微毛孔、折痕和边缘压纹
- 功能面料：低光泽、轻微编织纹和结构缝线

织纹尺度必须真实，禁止放大成麻袋纹。

### 7.2 金属与机械件

参考图库中的科幻载具和机械服装逻辑：

- 喷涂金属
- 裸露金属边缘
- 黑色橡胶
- 透明玻璃
- 磨砂复合材料
- 螺栓、接口、液压和线缆
- 不同粗糙度清楚分离

默认维护良好。只有原图明确存在旧化时，才保留有限、可解释的掉漆和使用痕迹。

禁止随机皲裂、密集划痕、锈蚀堆积和无意义机械细节。

### 7.3 图案、文字和标识

- 原图清楚可辨时，尽量保持位置、颜色和轮廓。
- 原图无法辨认时，使用干净无文字区域或简单非文字图形。
- 禁止生成乱码、随机英文和虚假品牌。

---

## 8. 电影灯光与皮肤层次

默认使用非均匀受光：

- 45度方向主光
- 较弱填充光
- 克制轮廓光
- 柔和环境遮蔽
- 轻微体积光
- 高动态范围但不过曝
- 面部一侧略亮、一侧保留柔和阴影
- 鼻翼、眼窝、下唇、下巴和颈部具有自然明暗转折

“光影颗粒”解释为：

- 真实微对比
- 克制电影颗粒
- 皮肤细微明暗变化

不得解释成脏点、粗大噪声或满脸黑斑。

### 灯光关键词

```text
Cinematic directional key light, asymmetric facial illumination, soft controlled fill, subtle rim light, physically correct subsurface scattering, soft ambient occlusion, gentle volumetric glow, natural highlight roll-off, preserved shadow detail, subtle filmic micro-contrast.
```

---

## 9. 阶段二完整提示词模板

```text
A premium feature-film full-body character asset with live-action photographic credibility, physically based material separation and restrained cinematic color. Preserve the design fidelity of a production-ready character asset while avoiding the clean generic CGI-render or digital-maquette look.

Perfectly replicate the complete structure, silhouette, proportions, final face contour, facial placement, final eyelid and eye-fissure shape, pupil position, gaze direction, hairstyle, outfit construction, accessories and pose strictly based on Image Prompt 1, the final clean black-and-white line art. Preserve only explicitly approved face-shape and eye-shape changes; keep the iris, pupils, gaze and all other facial features locked. Apply the original color palette, color blocking, patterns, markings and material assignments strictly based on Image Prompt 2, the original color illustration. Do not redesign, beautify, normalize or replace the character identity.

Image Prompt 3 is mandatory and must be the user-confirmed face look-development master. Replicate its facial identity, facial microstructure, gaze, skin or facial-material response and approved facial detail with highest priority. Use Image Prompt 3 for the face only; do not let it change body proportions, outfit, pose, full-body colors or accessories. If Image Prompt 3 is missing or unconfirmed, stop and generate the 9:16 strict-front portrait first; do not generate a full-body image.

Single character, strict front view, neutral standing pose, full body visible from head to feet, eye-level camera, 70mm to 105mm portrait lens, no perspective exaggeration, centered 9:16 vertical character asset presentation, clean neutral studio background.

Apply physically realistic skin only to visible human organic areas: scale-accurate visible pores, fine skin lines, subtle micro-wrinkles, fine vellus hair and follicles, physically correct subsurface scattering, natural non-uniform red and warm coloration around cheeks, nose, ears, eyelids, lips and fingertips, warm hydrated skin, realistic lips and eye moisture, subtle natural asymmetry and low-frequency tonal variation. Preserve the original age, species, facial expression and stylized proportions. Keep the result clean but never sterile, airbrushed, textureless or flat.

Render hair as layered natural fiber groups while preserving the original silhouette, parting, curls and color. Render fur or organic companions with directional micro-fur, never smooth plastic. Render clothes with correctly scaled fabric weave, seams and layered PBR textures. Render metal, glass, leather, rubber and composite parts with distinct physically based roughness and reflections.

Cinematic directional key light, asymmetric facial illumination, soft controlled fill, restrained negative fill, subtle rim light, physically correct subsurface scattering, soft ambient occlusion, natural highlight roll-off, preserved shadow detail, subtle organic filmic micro-contrast and fine luminance grain. The face must have clear but natural light and shadow variation, never flat or evenly illuminated. Grain must come from optical and luminance response, never dirt, grunge or coarse digital noise.

8k-quality appearance, ultra-fine controlled detail, clean silhouette, premium character asset fidelity. No base, no packaging, no toy scale, no text panel, no three-view board.
```

### 阶段二完整负面约束

```text
no redesign, no changed identity, no changed face shape, no changed gaze, no changed eyelids, no changed expression, no beautified influencer face, no realistic-human proportion replacement, no changed age, no changed species, no changed hairstyle, no changed outfit, no changed colors, no missing accessories, no extra accessories, no extra fingers, no fused fingers, no cropped head, no cropped feet, no side view, no three-quarter view, no side view sheet, no back view, no three-view board, no flat shading, no toon shading, no 2D outlines, no simplified materials, no wax skin, no plastic skin, no silicone mannequin, no porcelain face, no airbrushed skin, no sterile over-clean skin, no textureless smooth gradients, no uniform pores, no exaggerated wrinkles, no oily skin, no flat frontal lighting, no even illumination, no ring-light look, no passport-booth flash, no crushed shadows, no overexposure, no oversharpening, no excessive grain, no dirt-as-detail, no grunge overlay, no random cracks, no dense scratches, no clean generic CGI-render look, no game-character preview, no toy scale, no figurine base, no package, no text, no logo, no watermark, no UI
```

---

## 10. 阶段三｜皮肤和材质二次增强

只在阶段二结构、配色和人物身份正确后使用。

阶段三只允许修改：

- 皮肤微观质感
- 毛发细节
- 布料织纹
- 金属粗糙度
- 面部明暗层次
- 克制电影颗粒

禁止修改：

- 脸型
- 五官
- 眼神
- 表情
- 发型
- 身材
- 服装
- 配色
- 姿态
- 镜头
- 背景

### 阶段三标准命令

```text
只提升人物的皮肤、毛发、布料和材质真实度，其余全部锁定不变。

人类皮肤增加年龄适配的自然毛孔、极细皮纹、轻微微褶皱、细小绒毛与毛囊、真实次表面散射和克制的自然血色。鼻翼、耳朵、脸颊、嘴唇与指尖呈现细微红润变化，皮肤温润、有生命感，但不油腻、不脏污。

面部采用非均匀方向光，一侧由柔和主光照亮，另一侧保留自然阴影。增强眼窝、鼻翼、下唇、下巴和颈部的明暗转折，加入克制的电影微颗粒与皮肤微对比，不要均匀受光，不要磨皮，不要塑料感。

保持原人物脸型、五官、眼睑、瞳孔位置、视线方向、表情、发型、服装、配色、正面姿态、9:16构图和背景完全不变。
```

### 阶段三负面约束

```text
不要换脸，不要改变眼神，不要睁大眼睛，不要改变表情，不要改变年龄，不要改变发型，不要改变服装，不要改变颜色，不要改变姿态，不要改变构图，不要均匀受光，不要磨皮，不要蜡像皮肤，不要塑料皮肤，不要陶瓷脸，不要满脸夸张毛孔，不要成人皱纹套在儿童脸上，不要油亮高光，不要脏点，不要粗大噪声，不要过度锐化。
```

---

## 11. 自动命令

- 首次上传图片且尚未锁脸 → 不显示全身与三视图选项；显示状态 A 菜单，默认执行“生成9:16严格正面肖像照”。
- “2”／“先定脸”／“生成脸部定妆照”／“生成正面肖像” → 执行阶段一C，输出 9:16 严格正面头肩至上胸影视肖像，不输出腰部、腿和脚。
- 单图状态下执行“2” → 直接以该图同时锁定身份、结构和颜色，不要求用户补线稿。
- “转线稿” → 执行阶段一，输出正面 9:16 纯黑白线稿。
- “调整脸型为【类型】” → 在线稿上执行阶段一B，默认轻度；支持鹅蛋脸、菱形脸、圆脸、倒三角脸、长脸和方脸。
- “调整眼型为【类型】” → 在线稿上执行阶段一B，默认轻度；支持三角眼、桃花眼、狐狸眼、瑞凤眼和肿泡眼。
- “创建我的AI人物：脸型【类型】＋眼型【类型】” → 在线稿上组合调整两项，先输出预览，不进入写实阶段。
- “锁定这个人物” → 将当前结果确认为角色身份母版线稿，后续作为 Image Prompt 1。
- “图1根据图2进行提示词修正：先定脸” → 兼容旧调用句式；图1必须是最终纯黑白线稿，图2必须是原始彩色插画，执行阶段一C。不得沿用旧提示词中的 `collectible figurine`、`digital art toy feel`、`Octane / UE5 Lumen`、`flat bold colors` 或 `ultra-fine details everywhere`。
- “调整眉毛/眼睛/鼻子/嘴型/耳朵/脸部轮廓为【要求】” → 只在当前单脸开发稿上执行阶段一D；未指定五官、人物身份、质感、灯光和构图全部锁定。
- “锁定这张脸”／“确认这张脸”／“脸部母版确认” → 将当前单脸开发稿确认为最终脸部定妆母版和 Image Prompt 3，进入状态 C，并解锁全身与三视图。
- “恢复原脸型” → 撤销脸型调整，只恢复原线稿面部外轮廓，五官与眼神保持不变。
- “恢复原眼型” → 撤销眼型调整，只恢复原线稿眼睑与眼裂轮廓，瞳孔和视线保持不变。
- “线稿保持结构，原图保持颜色” → 仅在状态 C 执行阶段二，并强制加入 Image Prompt 3；未锁脸则转入阶段一C。
- “4”／“图1根据图2进行提示词修正：转全身”／“转全身”／“正面9:16全身” → 仅在状态 C 执行；未锁脸时禁止全身并自动返回 9:16 正面肖像流程。
- “人物三视图”“生成脸部特写＋人物三视图”或“图1根据图2进行提示词修正：人物三视图” → 仅在已执行“锁定这张脸”后执行阶段二A，输出左侧最终脸部特写＋右侧 FRONT/SIDE/BACK 的 16:9 横向人物身份设定板；未锁脸则先返回单脸开发流程。
- “5” → 与“人物三视图”相同；未锁脸时禁止执行并自动返回正面肖像流程。
- “转高写实人物资产” → 未锁脸时直接先生成 9:16 正面肖像；已锁脸时才允许以 Image Prompt 3 执行阶段二。
- “提升皮肤质感” → 只执行阶段三。
- “眼神不对” → 只恢复原图眼睑、瞳孔位置和视线方向。
- “不要塑料感” → 加强 SSS、微纹理和粗糙度变化，不改变五官。
- “正面9:16肖像” → 执行阶段一C，只输出头肩至上胸肖像。
- “正面9:16全身” → 仅在状态 C 输出完整全身；未锁脸时转为“正面9:16肖像”。
- “正面9:16” → 未锁脸时解释为正面肖像；已锁脸且用户明确说“全身”时才解释为完整全身。
- “以后做三视图” → 当前不执行，只保留正面资产作为未来结构基准。

---

## 12. 参考图库

风格参考目录：

`C:/Users/elliot/Desktop/高达机甲SKILL/机甲风格`

参考图：

- `08d184ff-1b63-4749-ab3a-3f3abfe51b17.webp`：插画式人物与科幻载具的结构、比例和硬表面分离。
- `86c7d88c-4514-4f88-9b9d-b43cb449b894.webp`：人物、机械服装、布料和大型载具的层级关系。
- `92931f3fcc5d88ad09af2c55099b327a.webp`：插画轮廓、异形机械面部和配色锁定。
- `ChatGPT_Image_2026年7月25日_23_10_59.png`：高写实 PBR 机械、玻璃、皮革和真实日光。
- `d5dfaa9e-aa11-4618-878d-e9e671f7451d.webp`：异形皮肤、眼周、颈部褶皱和布料材质。
- `C:/Users/elliot/Desktop/角色设定展板-正确眼神版.png`：正确眼神、皮肤毛孔、卷发、耳朵、手部和材质细节。

只学习材质、光影和转换逻辑，不复制参考图中的具体人物或载具设计。

---

## 13. 质量检查

生成前必须检查：

- [ ] 是否已正确识别状态 A、B 或 C，并且只显示当前阶段允许的命令
- [ ] 未锁脸时，菜单是否完全隐藏全身和三视图选项
- [ ] 未锁脸时，默认输出是否为 9:16 严格正面头肩至上胸肖像，而非全身
- [ ] 用户在未锁脸时输入“4”“5”“转全身”或“三视图”，是否已被门控拦截并返回肖像流程
- [ ] 是否为单一角色
- [ ] 是否为 9:16 正视角
- [ ] 若为脸部定妆模式，是否为严格正面头肩构图、脸部占画面高度约 45%—60%
- [ ] “证件照”是否只用于身份正面校验，而没有生成白底平光、直闪或磨皮质感
- [ ] 脸部是否存在尺度真实的可见毛孔、细皮纹、自然非均匀红润和低频肤色变化
- [ ] 脸部是否有明确但自然的明暗塑形与细微光影颗粒，而非脏点或数字噪声
- [ ] 是否避免过分干净、光滑、无纹理、无层次的通用 CGI 渲染感
- [ ] 若为全身资产模式，是否完整显示头部、手和脚
- [ ] 是否没有侧视图、背视图和三视图
- [ ] 线稿是否只有纯黑和纯白
- [ ] 若启用脸型调整，是否只改变了面部外轮廓
- [ ] 若启用眼型调整，是否只改变了眼睑、眼角和眼裂比例
- [ ] 调整后的瞳孔、视线、其他五官、表情、年龄和人物身份是否保持
- [ ] Image Prompt 1 是否只负责结构
- [ ] Image Prompt 2 是否只负责颜色和材质分区
- [ ] 若为全身或三视图，是否强制存在已确认的 Image Prompt 3
- [ ] Image Prompt 3 是否只锁定脸部身份与面部材质，没有污染身体、服装和姿态
- [ ] 若为人物三视图模式，是否为左侧脸部特写＋右侧 FRONT/SIDE/BACK，且没有规格表、细节框、文字或 UI
- [ ] 生成人物三视图前，是否已有用户明确确认的最终脸部定妆母版
- [ ] 三个全身视图是否等高、等比例、底部对齐，并且脸、发型、体型、服装、配色、材质、配饰完全一致
- [ ] SIDE 是否为严格 90 度侧面，BACK 是否为严格背面
- [ ] 头身比例是否保持
- [ ] 脸型和年龄是否保持
- [ ] 眼睑、瞳孔和视线方向是否保持
- [ ] 表情是否保持
- [ ] 发型、服装和配色是否保持
- [ ] 人体皮肤是否具有年龄适配的真实层次
- [ ] 非人类皮肤是否符合物种
- [ ] 机械件是否没有人类毛孔
- [ ] 布料、金属、玻璃和毛发是否正确分离
- [ ] 面部是否存在自然明暗变化
- [ ] 是否无蜡像、塑料、陶瓷和磨皮感
- [ ] 是否无随机皲裂和高频脏纹
- [ ] 是否无文字、Logo、水印和 UI

任何一项失败，只局部修正失败项，其余全部锁定。
