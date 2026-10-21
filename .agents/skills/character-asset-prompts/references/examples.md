# 调用与交付示例

## 简短需求 先问再写

用户：帮我写一个中世纪女骑士的提示词。
回复：已知是中世纪女性骑士。请补充：年龄感偏20多岁、30多岁还是40岁以上？画风偏写实、电影感3D还是2D？盔甲偏实战朴素还是华丽仪式感？不确定的项可以让我来定。
此时等待回答，不立即按自己想法交付完整提示词。

## 已有文本 直接提取

用户：角色林岚，38岁女骑士，深棕编发，左眉旧疤，钢甲与酒红披风，左腰长剑，电影感3D。生成中文四视图提示词。

中文正向提示词：
一张16:9横向角色设定图，同一位38岁女性骑士林岚的四种视图。左侧约四分之一为严格正面身份特写，完整头顶至下巴，含少量颈肩；右侧依次排列正面、从角色自身左侧观察的90度侧面、背面三个完整全身图，放松A姿势，同一尺度，脚底同一水平线，头顶与鞋底完整入画。各视图保持清晰间距，不互相遮挡。
深棕色编发，左眉有一道愈合旧疤，表情沉静。穿结构实用的钢制盔甲与酒红色披风，角色自身左腰佩一把带鞘长剑。所有视图保持同一脸部结构、年龄感、发型、服装、伤痕侧别和佩剑位置；背面不回头，侧面不是3/4角度。
电影感3D，可信金属反光和布料垂坠，避免塑料质感。纯白无缝背景，偏轴柔和主光和适度补光，保留五官与衣层体积，背景不吞没轮廓，稳定白平衡，弱透视，全身结构清楚。无文字、无标签、无水印，不出现无关人物，不裁切头脚。

中文锁定卡：林岚、38岁女性、深棕编发、左眉旧疤、钢制盔甲、酒红披风、左腰带鞘长剑、电影感3D。
设置建议：横向16:9；未指定工具，不添加平台专属参数。

## 用户要双语 附同义英文

将上面的完整中文放在前面，再提供以下独立英文版，不能只给英文：

One 16:9 landscape character reference sheet showing four views of the same 38-year-old female knight, Lin Lan. The left quarter contains an enlarged strict-front identity portrait with the complete crown and chin and a small amount of neck and shoulders. On the right, arrange front, exact anatomical left-side profile and back full-body views, in a relaxed A-pose, at equal scale with feet aligned on one baseline and complete heads and shoes visible. Keep clear spacing without overlap.
Dark chestnut braided hair, a healed scar through her anatomical left eyebrow, and a composed expression. Practical steel armor, a burgundy cloak, and one sheathed longsword at her anatomical left hip. Keep facial structure, apparent age, hairstyle, outfit, scar side and sword placement identical across views. The back view faces away without looking back; the side view is exactly 90 degrees, not three-quarter.
Cinematic 3D with believable metal reflections and cloth drape, avoiding plastic-looking materials. Pure white seamless background, a soft off-axis key and controlled fill preserving facial and costume volumes, no background spill erasing the silhouette, stable white balance, weak perspective and clear full-body structure. No text, labels, watermark, unrelated people or cropped heads and feet.

两种语言任选一种投喂，按语言分别计数。以上为输出格式示例，不表示已生成图片。

## 局部修改

用户：沿用C001，只把酒红披风改成墨绿，给中文。
处理：只更新披风色彩及锁定卡对应项，不重新问年龄、性别、风格，不添加新五官或道具。

## 用户授权代选

用户：设计一个无性别木制机器人，定格风，其余你定，不用提问。
处理：直接给中文设计和提示词，不问男女；木纹、关节、漆面等补充标为设计提案，不套人类毛孔、血管或虹膜模板。

## 美工深化：把空泛服装写成可建模结构

示例需求：设计一名32岁成年男性城市修复师，写实3D，深棕短卷发，深灰外套和墨绿工装裤，其余你定；只给16:9人物建模参考提示词。

初始描述“帅气、精致、电影级皮肤、深灰外套、工装裤”不足以锁定造型。授权范围内细化脸型、肩腰比例、领口/袖口/门襟、面料重量与鞋履，再给完整草案。以下为文字示范，未出图，新增外观尚未确认为主基准。

```text
制作一张16:9横向写实3D人物建模参考板，纯白无缝背景。同一名32岁成年男性城市修复师，左侧约四分之一为严格正面身份特写，完整头顶至下巴并含少量颈肩；右侧依次为正面、从人物自身左侧观察的严格90度侧面、背面三个完整全身视图，等高等比例，头顶与鞋底基线对齐，间距充足。

方圆脸，颧部起伏克制，下颌角明确但圆缓，下巴中等宽度。深棕色短卷发，头顶有自然卷束体积，两鬓收整，发际线完整；较平直的中等浓眉，横向杏仁眼，棕色虹膜，眼睑适度覆盖上缘，眼距自然。直鼻梁、圆钝鼻尖，薄上唇与适度饱满下唇，嘴角放松。暖米色肤色，体型精实，肩比骨盆略宽，头颈与四肢比例自然，不夸张肌肉。侧面额头、鼻梁、鼻唇和下巴构成可信连续轮廓。

穿深灰色短款工作夹克，长度到髋上缘，常规肩线、窄翻领、前中拉链闭合、直筒长袖与简洁扣合袖口；前胸一只平整贴袋，背部沿肩线延续横向拼接，不增加徽章。面料为有厚度的高密棉帆布，表面细织纹、哑光，肩肘处褶皱由姿态产生。内搭暖灰圆领棉质上衣，仅领口可见。墨绿色直筒工装裤，腰线自然，侧袋贴合外腿，不鼓成不合理体积；裤脚完整落在鞋面上方。深棕低帮系带工作鞋，皮质鞋面有克制柔和反射、圆鞋头与适度厚度的深色橡胶底，左右成对。干净状态，不额外加入污渍、破损、伤痕、工具或手持物。

人物采用放松A姿，双臂微离躯干，手指放松，双腿自然不交叉，双脚完整接地；正面与背面严格朝向对应机位，侧面头、肩、骨盆与鞋方向一致，背面不回头。三视图保持同一脸型、卷发轮廓、体型、肩线、衣袋、闭合结构、裤袋位置与鞋款，不能重新设计背面。

采用可信形体与PBR材质的写实3D表达，皮肤微纹理适度，发束先有体块再有细发丝，棉帆布、棉上衣、皮鞋和橡胶底呈现不同粗糙度与反射。偏轴柔和主光、适度补光和克制分离光，五官及衣层起伏可读，曝光与白平衡一致，白背景不吞没轮廓，脚底轻接触阴影，全身景深足以看清手足和衣缝。

只展示这一角色的一个身份特写与三个全身方向，不增加无关人物、文字、编号、标尺、网格、边框、水印或环境；不出现脸部漂移、镜像造型、45度侧面、裁切头脚、肢体畸形、塑料皮肤、过度锐化或强景深虚化。
```

## 已确认美型CG：优化材质不换脸

示例需求：参考人物已经确认，只提高发丝、皮肤和衣料质量，保留美型CG。
处理：锁定原眼裂/瞳距/虹膜比例、鼻唇、年龄感、脸型与既有造型。change只包括主次发束、低强度CG皮肤微纹理、衣料厚度与受光；preserve包括身份和半写实媒介。不能加入S04/S16的“no CGI”或粗大真人毛孔，不改变服装剪裁或把白底四视图改成写真。

## 指定S16转换但尚未确认脸

示例需求：用S16把原插画转成高写实人物三视图，脸尚未确定。
处理：完成身份开发所需的正面肖像提示词与美工细化，说明后续三视图待脸部确认；不伪造已锁脸或已生成图片。已有明确确认则沿用，不要求用户重复确认。

## 剧本角色编号与局部换装

示例需求：沿用@CH-002，脸发不动，只把外套换成深蓝短夹克。
处理：角色ID仍为@CH-002；保留年龄、体型、左右标记、画风与当前版式，只更新授权外套的肩线、领口、袖口、闭合、长度及材质，登记同一身份的服装新版本。三视图同步，不生成C001新身份，也不顺手换裤鞋。
