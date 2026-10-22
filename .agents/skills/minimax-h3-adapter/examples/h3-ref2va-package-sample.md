# 精简制作包

## 固定资产

### 角色 CHAR_01｜粉西装青年
#### 图片提示词
```text
16:9 白底人物资产板，四视图：左正面身份特写＋右完整正/左侧/背全身，亮粉西装外套配粉长裤，卷曲金发，怀里抱一只黑羊。
```

### 场景 LOC_01｜黄昏草坡
#### 图片提示词
```text
16:9 场景资产板，全景单幅：金色夕阳下的草坡，远处白羊群，空气通透暖金侧光。
```

## 剧集 E01｜追风

### 小说原文
```text
他抱着羊站在草坡上，说要追风。
```

### 片段 S01｜10秒｜追风

角色：CHAR_01
场景：LOC_01

#### 视频提示词
```text
subject_definitions:
<Subject 1> is the young man from <Picture 1>, with short wavy blonde hair, a bright pink suit jacket and matching trousers, holding a small black lamb in his arms.
<Subject 2> is the golden-hour hillside in <Picture 2>, with dry grass, warm low sunlight from the left and a distant white flock on the ridge.

summary:
[reference generation] The target video shows <Subject 1> standing on <Subject 2>, holding the lamb and delivering the line about following the wind.

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - the blonde hair, pink suit, silver rings and the black lamb in his arms are retained.
<Subject 2> (appears in [Shot 1]): fully_preserved - the dry grass, warm golden-hour side light and the distant white flock are retained.

detailed_description:
The target video is in realistic photographic style with warm golden-hour lighting and shallow depth of field.
[Shot 1] The shot begins from <Picture 1>, showing <Subject 1> standing on <Subject 2>, holding a small black lamb securely in his arms while the warm light rims his pink jacket. The camera pushes in with small amplitude at slow speed as he looks toward the open ridge and speaks with a calm, low male voice (S1), saying: <d>[English] Follow the wind, live free.</d> He shifts his weight and cradles the lamb closer while the breeze lifts the edge of his jacket. As his voice stops, his lips close into a relaxed line, his gaze stays on the horizon, and the camera holds on this quiet state through the end of the video.

overall_soundscape: A steady low wind moves through the dry grass, with the distant bleating of the white flock and the soft rustle of the pink suit fabric.

non_diegetic_music: A sparse acoustic guitar pattern at a slow tempo with a sustained low cello underneath, fading out before the final frame.
```
