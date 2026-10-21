# ZHIFEIJIAI｜Beauty Portrait Master v3.0

> 模块化高端商业女性写真生成系统  
> 适用于 ChatGPT 图像生成、Midjourney、Flux、Nano Banana、即梦、可灵、Sora、Seedance 等。

## 一、SKILL 名称

**ZHIFEIJIAI_BEAUTY_PORTRAIT_MASTER_v3.0**

## 二、系统定位

本 SKILL 专门用于生成、反推和重构以下类型的女性视觉内容：

- 高端商业美妆女性写真
- 护肤品广告人物
- 韩系高端写真
- 冷蓝美妆人像
- 暖灰护肤广告
- 高级棚拍近景
- 女性特写与极特写
- 参考图人物质感反推
- 同一人物多景别提示词
- 动态口播与短视频人物一致性提示词

系统采用模块化拼接结构：

```text
摄影风格
+ 灯光系统
+ 镜头系统
+ 人物设定
+ 皮肤系统
+ 肤色系统
+ 妆发造型
+ 构图景别
+ 动作表情
+ 商业修图
+ 负面限制
```

核心目标：

> 生成像真实商业摄影棚完成的高端女性美妆广告，而不是 AI 美女图。

## 三、执行顺序

必须严格按照以下顺序组织提示词：

1. 摄影风格
2. 灯光结构
3. 镜头与光学
4. 人物年龄与外观
5. 皮肤表面结构
6. 皮肤内部通透
7. 肤色与血色
8. 妆面、发型、服装、配饰
9. 构图与景别
10. 动作与表情
11. 商业修图逻辑
12. 背景与色彩
13. 负面提示词

## 四、默认参数

```text
26-year-old adult East Asian woman
vertical 9:16 composition
medium close-up beauty portrait
85mm portrait lens
luxury skincare campaign
soft wraparound beauty lighting
healthy ivory-beige translucent skin
neutral warm-gray seamless background
```

# 第一部分｜摄影风格库

## 五、摄影风格预设

### 5.1 高端护肤广告

```text
ultra-premium luxury skincare campaign,
high-end commercial beauty photography,
clean premium cosmetics hero portrait,
refined East Asian beauty advertising aesthetic
```

### 5.2 韩系高端写真

```text
Korean luxury beauty editorial,
soft refined portrait photography,
delicate feminine atmosphere,
clean luminous complexion,
intimate high-end studio portrait
```

### 5.3 冷蓝美妆人像

```text
cool blue luxury beauty portrait,
high-key commercial cosmetics photography,
soft cyan-blue studio atmosphere,
warm ivory skin contrasting against a cool background
```

### 5.4 暖灰护肤棚拍

```text
warm neutral luxury skincare portrait,
soft beige-gray studio photography,
minimal premium advertising composition,
quiet refined commercial mood
```

### 5.5 时尚杂志美妆

```text
high-fashion beauty editorial,
premium magazine portrait photography,
refined cosmetics styling,
controlled dramatic elegance
```

### 5.6 电影感商业人像

```text
cinematic commercial beauty portrait,
soft filmic contrast,
organic highlight response,
restrained luxury color grading
```

# 第二部分｜灯光系统

## 六、标准灯光库

### 6.1 正面包裹柔光

```text
large frontal diffused beauty light,
oversized octabox positioned slightly above eye level,
large white reflector beneath the face,
soft bilateral fill,
very low lighting ratio,
extremely smooth shadow transitions
```

### 6.2 45°护肤广告光

```text
oversized octabox key light positioned very close at 45 degrees,
large frontal reflector,
soft beauty fill beneath the face,
gentle negative fill on the opposite side,
soft wraparound illumination
```

### 6.3 蝴蝶光

```text
soft butterfly beauty lighting,
key light centered above eye level,
delicate shadow beneath the nose,
subtle cheekbone shaping,
clean luxury cosmetics lighting
```

### 6.4 冷蓝轮廓光

```text
soft cool-blue ambient background light,
subtle cyan rim light along the hair,
gentle separation between dark hair and background,
no harsh edge lighting
```

### 6.5 奶油高调光

```text
high-key cream-toned beauty lighting,
soft luminous exposure,
pearl-like highlights,
creamy highlight roll-off,
bright but protected skin tones
```

### 6.6 窗光写真

```text
soft north-facing window light,
large natural diffused source,
gentle side illumination,
quiet tonal falloff,
natural editorial softness
```

# 第三部分｜镜头与光学系统

## 七、镜头预设

### 7.1 85mm 商业肖像

```text
85mm premium portrait lens,
natural facial compression,
precise focus on the eyes,
shallow depth of field,
elegant commercial rendering
```

### 7.2 100mm 美妆特写

```text
100mm macro beauty portrait lens,
precise focus on both eyes and cheek skin,
high local detail,
soft facial edge rendering,
premium beauty campaign optics
```

### 7.3 120mm 极特写

```text
120mm macro lens,
extreme close-up skin rendering,
precise epidermal detail,
minimal facial distortion,
controlled depth of field
```

### 7.4 中画幅系统

```text
Hasselblad H6D or Phase One IQ4 medium-format rendering,
organic skin tonality,
delicate tonal separation,
high dynamic range,
premium commercial color response
```

### 7.5 动态电影机系统

```text
ARRI Alexa Mini LF or Sony Venice 2,
soft cinematic highlight roll-off,
stable skin color rendering,
natural motion response
```

### 7.6 光学柔化

```text
Black Pro-Mist 1/8 diffusion filter look,
subtle optical bloom,
gentle lens-based diffusion,
soft edge transitions,
no digital blur
```

# 第四部分｜人物设定系统

## 八、默认人物

```text
26-year-old adult East Asian woman,
natural youthful facial structure,
realistic East Asian facial proportions,
subtle facial asymmetry,
refined but believable beauty,
elegant and approachable,
not doll-like,
not influencer-style
```

## 九、人物气质预设

### 9.1 温柔亲和

```text
gentle approachable expression,
soft relaxed eyes,
subtle warm smile,
calm natural presence
```

### 9.2 冷艳高级

```text
restrained confident expression,
calm direct gaze,
cool elegant presence,
minimal emotional display
```

### 9.3 轻熟暧昧

```text
intimate direct eye contact,
slightly playful expression,
soft parted lips,
restrained sensuality,
elegant rather than provocative
```

### 9.4 清冷自然

```text
quiet neutral expression,
soft distant gaze,
clean understated elegance,
cool refined temperament
```

# 第五部分｜皮肤系统

## 十、商业真实皮肤

```text
authentic commercial photographic skin realism,
naturally refined human skin texture,
controlled micro-pores visible only upon close inspection,
delicate natural skin grain,
soft epidermal texture,
subtle peach fuzz,
fine follicle texture,
realistic under-eye texture,
realistic lip lines,
tiny natural surface irregularities
```

## 十一、皮肤通透系统

```text
advanced multilayer skin subsurface scattering,
multi-layer epidermis and dermis light transport,
light softly penetrating the epidermis and naturally returning through the dermis,
natural internal skin luminosity,
soft dermal translucency,
subtle blood-rich translucency,
skin illuminated from within
```

## 十二、水润与皮脂系统

```text
healthy water-rich epidermis,
fresh moisturized complexion,
restrained natural facial sebum,
controlled healthy skin sheen,
localized hydrated highlights,
non-greasy luminosity,
soft water-light reflection
```

## 十三、皮肤高光系统

```text
creamy highlight roll-off,
soft pearl-like specular highlights,
silky tonal transitions,
smooth highlight compression,
localized highlights on the forehead, nose bridge, upper cheeks, chin and lips
```

## 十四、特写皮肤增强

```text
controlled micro-pores,
fine natural skin grain,
delicate peach fuzz,
realistic under-eye texture,
subtle epidermal micro-roughness,
slight chromatic skin variation,
precise macro-level photographic detail
```

特写时降低：

```text
heavy bloom,
strong diffusion,
over-soft skin,
excessive glow
```

# 第六部分｜肤色系统

## 十五、肤色预设

### 15.1 象牙白

```text
healthy ivory-beige complexion,
soft peach undertones,
subtle rosy circulation,
natural chromatic variation
```

### 15.2 冷白皮

```text
cool ivory complexion,
neutral pink undertones,
delicate translucent skin,
subtle cool facial tonality
```

### 15.3 奶油肌

```text
soft creamy beige complexion,
milky tonal softness,
warm pearl undertones,
gentle luminous finish
```

### 15.4 蜜桃肤色

```text
soft peach-beige complexion,
gentle rosy warmth,
fresh youthful circulation,
warm healthy luminosity
```

### 15.5 香槟肤色

```text
champagne beige complexion,
soft golden-peach undertones,
refined warm luminosity,
premium commercial skin tone
```

### 15.6 健康自然肤色

```text
balanced natural beige complexion,
subtle warm-red undertones,
realistic blood circulation,
healthy non-pale skin
```

# 第七部分｜妆发造型系统

## 十六、妆面预设

### 16.1 护肤广告妆

```text
clean refined makeup,
sheer breathable foundation,
natural skin still visible beneath makeup,
soft peach blush,
lightly defined eyebrows,
subtle brown eyeliner,
natural lashes,
hydrated nude-pink lips
```

### 16.2 韩系精致妆

```text
refined Korean beauty makeup,
soft luminous base,
delicate eyeliner,
separated natural lashes,
subtle peach-beige eyeshadow,
clear nude glossy lips
```

### 16.3 清冷妆

```text
cool neutral makeup,
soft taupe eye definition,
muted rose lips,
restrained blush,
clean refined skin finish
```

## 十七、发型预设

### 17.1 干净盘发

```text
dark hair pulled back into a clean natural updo,
soft loose strands around the temples and ears,
realistic baby hairs along the hairline
```

### 17.2 中分长卷发

```text
long dark brown hair with soft natural waves,
clean center part,
loose strands framing the cheeks,
silky realistic hair texture
```

### 17.3 自然披发

```text
long naturally flowing dark hair,
soft movement,
fine individual strands,
clean commercial styling
```

## 十八、服装与配饰

默认：

```text
minimal ivory or champagne-beige satin top,
clean neckline,
small pearl earrings
```

冷蓝韩系写真：

```text
minimal black or ivory strapless top,
silver teardrop earrings,
bare shoulders and collarbones
```

# 第八部分｜构图与景别系统

## 十九、标准景别

### 19.1 全身

```text
full-body portrait,
entire figure visible from head to toe,
complete hands and feet,
50mm to 70mm lens
```

### 19.2 七分身

```text
three-quarter-length portrait,
framed from the head to below the knees,
hands fully visible,
50mm to 85mm lens
```

### 19.3 半身

```text
waist-up portrait,
upper body and hands visible,
70mm to 85mm lens
```

### 19.4 中近景

```text
medium close-up beauty portrait,
framed from the upper chest upward,
complete head, shoulders, neck and collarbones visible,
face occupying approximately 45 to 55 percent of the frame
```

### 19.5 近景

```text
close-up beauty portrait,
framed from the shoulders upward,
face occupying approximately 60 percent of the frame
```

### 19.6 特写

```text
tight facial beauty close-up,
face occupying approximately 70 to 85 percent of the frame,
framed from the upper forehead to just below the chin,
100mm macro beauty lens
```

### 19.7 极特写

```text
extreme close-up beauty portrait,
only part of the face fills the frame,
one eye, cheek, nose and lips visible,
120mm macro lens
```

## 二十、构图触发规则

```text
再近一点 → 提升一级景别
远一点 → 降低一级景别
测试皮肤 → 默认特写
测试通透感 → 默认 100mm 美妆特写
人物口播 → 默认中近景
展示服装 → 默认半身或七分身
```

# 第九部分｜动作与表情库

## 二十一、静态动作预设

### 21.1 直视镜头

```text
direct eye contact,
calm relaxed posture,
subtle natural expression
```

### 21.2 手靠近嘴唇

```text
one hand gently raised toward the lips,
fingertips softly resting near the lower lip,
elegant relaxed fingers,
intimate but restrained gesture
```

### 21.3 托下巴

```text
one hand gently supporting the chin,
relaxed fingers,
clean elegant beauty pose
```

### 21.4 摸头发

```text
one hand lightly touching the hair near the temple,
natural feminine gesture,
relaxed wrist and fingers
```

### 21.5 轻微回眸

```text
subtle over-the-shoulder glance,
soft head turn,
eyes returning toward the camera
```

### 21.6 自然微笑

```text
subtle warm smile,
gentle cheek movement,
soft expression through the eyes
```

# 第十部分｜商业修图系统

## 二十二、修图逻辑

```text
premium commercial beauty retouching,
natural skin preserved beneath refinement,
soft global contrast,
high local skin detail,
refined tonal separation,
no plastic smoothing,
no artificial facial reshaping
```

# 第十一部分｜背景色彩系统

## 二十三、背景预设

### 23.1 暖灰

```text
neutral warm-gray seamless studio background,
subtle beige undertone,
soft warm gradient
```

### 23.2 冷蓝

```text
cool desaturated blue seamless background,
soft cyan-blue gradient,
clean luxury studio atmosphere
```

### 23.3 奶油白

```text
soft cream seamless background,
warm ivory undertone,
high-key minimal beauty setting
```

### 23.4 珍珠灰

```text
pearl-gray studio background,
soft luminous neutrality,
refined premium cosmetics mood
```

# 第十二部分｜参考图反推系统

## 二十四、触发条件

用户上传图片并说“反推、提取人物质感、提取皮肤和光影、根据这张图写提示词、按这种风格出图”时，自动进入参考图反推模式。

## 二十五、反推分析顺序

1. 人物年龄与族裔外观
2. 脸型和五官比例
3. 妆面
4. 发型与配饰
5. 皮肤表面结构
6. 通透与高光
7. 肤色系统
8. 灯光方向与软硬
9. 镜头、焦段和景深
10. 景别与构图
11. 背景色彩
12. 商业风格
13. 完整提示词
14. 负面提示词

## 二十六、继承规则

默认只继承：皮肤、灯光、镜头、色调、妆面语言、构图和商业风格。

```text
inherit only the skin texture, lighting, color palette, makeup language and photographic style,
do not replicate the exact face
```

用户明确要求保持同一人物时才加入：

```text
strictly preserve the same facial identity,
maintain the same facial proportions,
keep the same eyes, nose, mouth, jawline, hairstyle and overall appearance
```

# 第十三部分｜同一人物多景别系统

## 二十七、一致性锁定

```text
the same adult East Asian woman across every framing,
strictly consistent facial identity,
identical hairstyle, makeup, clothing, accessories and skin tone,
only the camera distance, focal length and framing change
```

# 第十四部分｜动态视频系统

## 二十八、动态一致性

```text
The same adult East Asian woman remains visually identical throughout the entire shot.
Her facial identity, hairstyle, makeup, clothing, accessories, skin tone and age remain consistent.
No identity drift, no facial morphing, no changing jawline, eyes, nose or lips.
```

## 二十九、动态皮肤一致性

```text
The natural commercial skin texture remains stable throughout the entire shot.
Micro-pores, subtle peach fuzz, under-eye texture, lip texture, hydrated highlights and tonal variation remain consistent.
No skin texture flicker, no waxy transitions, no sudden smoothing, no changing skin color.
```

## 三十、口型与牙齿

```text
natural restrained lip movement,
accurate articulation,
stable lip shape,
consistent teeth,
no oversized mouth opening,
no deformed teeth,
no lip warping
```

## 三十一、眼睛与表情

```text
natural blinking,
stable eye shape,
consistent iris color,
subtle eye moisture,
realistic catchlights,
restrained micro-expressions
```

## 三十二、手部动态

```text
anatomically correct hands,
five fingers on each hand,
natural finger spacing,
smooth slow movement,
no extra fingers,
no fused fingers,
no warped hand
```

## 三十三、推荐镜头运动

优先：

```text
locked-off camera
very slow cinematic push-in
subtle lateral slide
```

避免：

```text
rapid orbit
fast zoom
strong handheld shake
dramatic camera rotation
```

# 第十五部分｜自动修正机制

## 三十四、皮肤太塑料

```text
subtle chromatic skin variation,
natural skin grain,
controlled micro-pores,
organic skin tonality,
realistic epidermal micro-roughness
```

## 三十五、皮肤太油

```text
restrained hydrated sheen,
localized moisture highlights,
controlled non-greasy luminosity
```

## 三十六、不够通透

```text
advanced multilayer subsurface scattering,
natural dermal translucency,
internal skin luminosity,
subtle blood-rich translucency,
creamy highlight roll-off
```

## 三十七、人物像网红脸

```text
natural East Asian facial proportions,
subtle facial asymmetry,
realistic jawline,
believable nose structure,
natural eye spacing,
non-influencer beauty
```

## 三十八、特写不够真实

```text
100mm macro beauty lens,
controlled micro-pores,
fine peach fuzz,
realistic under-eye texture,
realistic lip lines,
precise focus on the eyes and cheek skin
```

# 第十六部分｜Prompt 自动拼接模板

## 三十九、模块化组合公式

```text
[摄影风格]
+ [灯光]
+ [镜头]
+ [人物]
+ [皮肤]
+ [肤色]
+ [妆发]
+ [构图]
+ [动作]
+ [修图]
+ [背景]
+ [负面提示词]
```

## 四十、冷蓝韩系特写组合示例

```text
韩系高端写真
+ 正面包裹柔光
+ 冷蓝轮廓光
+ 100mm 美妆特写
+ 26岁成年东亚女性
+ 象牙白通透皮肤
+ 韩系精致妆
+ 中分长卷发
+ 手靠近嘴唇
+ 冷蓝背景
+ 商业修图
```

# 第十七部分｜标准完整模板

## 四十一、冷蓝韩系高端女性特写 Prompt

```text
Ultra-premium Korean luxury beauty editorial, photorealistic high-end commercial cosmetics photography, cool blue luxury beauty portrait, clean refined studio aesthetic.

Large frontal diffused beauty light positioned slightly above eye level, oversized octabox close to the subject, large white reflector beneath the face, bilateral soft fill, very low lighting ratio, extremely smooth shadow transitions, subtle cool-blue rim light along the hair, large soft catchlights in both eyes.

Shot on Hasselblad H6D or Phase One IQ4 medium-format camera, premium 100mm macro beauty portrait lens, f/2.8, precise focus on both eyes and cheek skin, shallow depth of field, Black Pro-Mist 1/8 diffusion filter look, subtle optical bloom, soft facial edge rendering, creamy highlight roll-off.

26-year-old adult East Asian woman, realistic East Asian facial proportions, subtle facial asymmetry, refined but believable beauty, slim oval face, softly tapered jawline, warm brown almond-shaped eyes, delicate nose bridge, naturally full nude peach-pink lips, direct eye contact, calm intimate slightly playful expression.

Authentic commercial photographic skin realism, naturally refined human skin texture, controlled micro-pores visible only upon close inspection, delicate skin grain, soft epidermal texture, subtle peach fuzz, realistic under-eye texture, realistic lip lines, tiny natural surface irregularities.

Advanced multilayer skin subsurface scattering, light softly penetrating the epidermis and naturally returning through the dermis, natural internal skin luminosity, soft dermal translucency, subtle blood-rich translucency, skin illuminated from within.

Healthy ivory-beige complexion with soft peach undertones, subtle rosy circulation, gentle capillary warmth around the cheeks and nose, slightly cooler jawline and neck, delicate chromatic variation.

Healthy water-rich epidermis, restrained natural facial sebum, controlled healthy skin sheen, localized hydrated highlights on the forehead, nose bridge, upper cheeks, chin and lips, non-greasy luminosity, soft pearl-like skin reflections.

Long dark brown hair with soft natural waves, clean center part, loose strands framing the cheeks, realistic baby hairs, refined Korean beauty makeup, sheer luminous foundation, soft peach-beige eyeshadow, delicate eyeliner, separated natural lashes, hydrated nude glossy lips, silver teardrop earrings, minimal black or ivory strapless top.

Vertical 9:16 close-up beauty portrait, framed from the top of the head to the upper chest, face occupying approximately 65 to 70 percent of the frame, one hand gently raised toward the lips, fingertips softly resting near the lower lip, elegant relaxed fingers, centered balanced composition.

Premium commercial beauty retouching, natural skin preserved beneath refinement, soft global contrast, high local detail, refined tonal separation, no plastic smoothing, no artificial facial reshaping.

Cool desaturated blue seamless studio background, subtle cyan-blue gradient, warm ivory skin contrasting against the cool background, clean luxury beauty atmosphere.

No CGI, no 3D render, no AI illustration, no anime, no doll-like face, no influencer face, no exaggerated V-line jaw, no childlike appearance, no waxy skin, no plastic skin, no porcelain skin, no completely smooth skin, no exaggerated pores, no oily face, no wet glossy skin, no metallic highlights, no gray skin, no orange skin, no excessive pink skin, no heavy contouring, no oversized false eyelashes, no exaggerated lip filler, no harsh sharpening, no hard flash, no distorted hands, no extra fingers, no fused fingers, no text, no logo, no watermark.
```

# 第十八部分｜输出格式

## 四十二、用户要求提示词

```text
【风格选择】
【灯光】
【镜头】
【人物】
【皮肤】
【构图】
【完整正向提示词】
【负面提示词】
```

## 四十三、用户要求直接出图

- 不解释，直接执行
- 未指定比例默认 9:16
- 未指定景别默认中近景
- 测试皮肤默认特写
- 测试通透感默认 100mm 特写

## 四十四、最终执行命令

必须严格按照：

**ZHIFEIJIAI_BEAUTY_PORTRAIT_MASTER_v3.0**

执行。

# 最终判断标准

- 是真实摄影，不是 CG
- 是商业美妆，不是普通自拍
- 皮肤真实但经过专业修饰
- 通透但不油
- 柔和但不糊
- 年轻但不幼态
- 高级但不网红
- 多景别保持同一人物
- 动态视频无脸漂移与皮肤闪烁

> 视觉结果必须像真实高端商业美妆摄影，而不是 AI 生成的漂亮女性。
