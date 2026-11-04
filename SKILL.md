---
name: explainer-video
description: 制作“黑底科普讲解视频”（3Blue1Brown / 网络技术科普风格）：中文 AI 旁白 + 字幕 + 逐帧程序化动画（代码面板、矩阵、柱状图、流程图、公式），最终输出 1080p MP4。用户只要提到“做成视频”“科普视频”“讲解视频”“加旁白/配音/字幕”“把这段代码/论文/概念讲清楚的视频”，或者给出一份代码、注释、知识点并希望生成视频（即使没说“动画”或“skia”），都应使用本技能。适用于讲解算法、模型结构（GPT、Transformer、分词器等）、源码逐行解读、数学推导等技术主题。
---

# 黑底科普讲解视频

把一个技术主题做成带中文配音、字幕和丰富动画的讲解视频。全部用代码生成：
skia 逐帧绘制画面 → edge-tts 生成旁白 → numpy 混音（背景铺底 + 转场音效）→ ffmpeg 拼接成片。
不需要 GPU，也不需要视频剪辑软件。

已有成功案例（同一套流程）：GPT 逐行拆解（9:43）、Transformer 全流程（14:42）、Bigram 逐行详解（12:36）、minbpe 分词器（12:45）。

## 文件布局

```
<技能目录>/
├── scripts/        引擎与流水线（new_project.sh 会复制到项目里）
│   ├── eng.py      绘图引擎：文字/形状/向量/代码面板/背景
│   ├── common.py   Ctx 时间工具 + 常用组件（矩阵、柱状图、坐标轴、token 块…）
│   ├── make.py     时间线、混音、字幕、渲染、拼接（命令：info / still / seg / audio / final）
│   ├── tts.py      edge-tts 批量生成旁白 → audio/*.mp3 + meta.json
│   ├── say.py      朗读文本规范化：数字、英文术语、多音字
│   ├── check.py    每 0.25s 渲染一帧找报错（不写文件，快）
│   ├── sheets.py   每句话 85% 处截一帧，拼成 2×2 联系表供目检
│   ├── render_all.sh  双进程并行渲染 → 混音 → 成片
│   ├── setup_env.sh   准备共享环境（首次 / 换机器时）
│   └── new_project.sh 新建项目
├── templates/      config.py、script.py、scenes.py、scenes_a.py 模板
├── references/
│   ├── engine_api.md  绘图 API、安全区、场景写法套路 —— 写场景代码前必读
│   └── narration.md   旁白写法、读音规则、字幕 —— 写脚本前必读
└── assets/gl_stub.c   无 GPU 服务器上 skia 需要的 libEGL/libGL 空实现
```

共享运行环境在 `~/.local/share/explainer-video/{venv,fonts,stub}`，项目目录通过软链使用，避免每个项目复制 300MB。

## 工作流程

### 0. 准备
```bash
bash <技能目录>/scripts/new_project.sh <工作目录>/build_<主题> "<右上角标签>"
```
环境缺失时它会自动调用 setup_env.sh（需要联网：uv、PyPI、GitHub 字体）。
**所有 python 命令都要带 `LD_LIBRARY_PATH=$PWD/stub`**，否则 skia 会报 `libEGL.so.1` 缺失。
先 `df -h .` 看一眼磁盘：每分钟成片约 4MB，中间文件（seg/ + audio/）约为成片的 2 倍。

### 1. 理解素材，必要时先调研
- 用户给了代码：通读，**自己跑一遍小例子**拿到真实数字（例如 BPE 的合并规则、token 数、loss），视频里展示真实结果，可信度高很多。代码不完整就去拉源仓库。
- 用户要求“先搜索参考视频”时，先用 WebSearch 看同类视频的风格与结构，再动手。
- 用户给的材料简略时要主动扩充：动机、原理、为什么这么设计、常见误区、和上下游的衔接。用户给了学习路线（如“手算 → 小例子 → 源码 → 接回项目”）就严格按它组织章节。

### 2. 写旁白脚本 `script.py`
先读 `references/narration.md`。要点：
- 15~22 个场景，每个场景 3~8 句；每句是一个动画锚点，所以按“画面要变化的地方”断句。
- 数字、英文术语、多音字的处理见 narration.md；写完**打印全部朗读文本通读一遍**。
- 同步改 `config.py`：TAG、项目特有的 EXTRA_EN / EXTRA_POLY。

### 3. 生成配音，确定时间线
```bash
venv/bin/python tts.py                 # 并发 4 路，失败自动重试；输出总时长
LD_LIBRARY_PATH=$PWD/stub venv/bin/python make.py info   # 每个场景的起点、时长、各句 cue
```
后续若改了某句旁白：删掉对应 `audio/<场景>_<序号>.mp3` 再跑 tts.py（只会补生成缺失的）。
旁白一变时间线就变，受影响场景要重新渲染。

### 4. 写场景动画
先读 `references/engine_api.md`。每个场景一个函数 `s_<id>(cv, S)`，放进 scenes_*.py（每个文件 500~900 行为宜，按章节拆分），在 `scenes.py` 的 SCENES 里注册，键与 script.py 的 id 一致。

设计原则（这是这类视频好不好看的关键）：
- **每句旁白都要有对应的画面变化**：说到什么就出现/高亮什么，用 `S.c(i)`、`S.m(i, f)` 对齐。
- 一个场景内用 `S.phase(i, j)` 划分 2~5 个画面阶段，阶段之间互斥，避免元素堆叠。
- 动效要丰富但克制：描边勾勒、回弹弹出、发光强调、流动光点、矩阵逐格扫描、序列合并的位移动画、代码行高亮与右侧演示联动。
- 配色语义固定：输入/中性用蓝，强调用黄，正确/输出用绿，错误/梯度用红，代码面板在左、演示在右。
- 数据型画面（矩阵、概率、计算步骤）用真实计算得出，并在场景函数外预计算好。

### 5. 自检（必须做，不要跳过）
```bash
LD_LIBRARY_PATH=$PWD/stub venv/bin/python check.py            # 抓异常（边界帧最容易出错）
LD_LIBRARY_PATH=$PWD/stub venv/bin/python sheets.py [场景id…]   # 生成 sheets/<id>_<n>.png
```
然后用 Read 工具**逐张查看联系表图片**，检查：文字重叠、超出屏幕边缘、内容压到字幕区（y>920）、阶段切换残留、空白画面、数字与旁白不一致。修完只对改过的场景重新 sheets。这一步通常要两三轮，能发现绝大部分问题。

### 6. 渲染与成片
```bash
bash render_all.sh "<输出路径>.mp4"     # 用 Bash 的 run_in_background 跑，等完成通知
```
- 2 核 CPU 上渲染约为实时的 1/6 ~ 1/12（机器有其他负载时更慢）：15 分钟成片要 1~2 小时。开始前告诉用户预计时长。
- 等待时不要用 sleep 轮询；用后台命令 + 完成通知，或 Monitor 的 until 循环。
- 某个进程崩溃（日志里有 Traceback）：修 bug → 用 `make.py seg <未完成的场景…>` 补渲染 → `make.py audio` → `make.py final <out>`。
- 混音（audio）必须在渲染全部结束后再跑，小内存机器上并行会被 OOM 杀掉。

### 7. 验收与交付
```bash
FF=$(venv/bin/python -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
$FF -i out.mp4 2>&1 | grep -E "Duration|Stream"                       # 时长、音视频流
$FF -i out.mp4 -af volumedetect -vn -f null - 2>&1 | grep mean_volume  # 约 -21 dB 为正常
$FF -v error -y -ss 300 -i out.mp4 -frames:v 1 frame.png              # 抽帧看一眼（避开转场淡入）
```
交付时告诉用户：输出路径、时长/分辨率/大小、章节内容概要、读音怎么处理的、哪些数值是真实运行结果、哪些是示意；并如实说明“没有完整观看全片、只抽查了关键帧”。工程目录可删除以释放空间。

## 常见问题

| 现象 | 原因与处理 |
|---|---|
| `ImportError: libEGL.so.1` | 没带 `LD_LIBRARY_PATH=$PWD/stub` |
| 某个字符显示成方块 | 四种字体都没有该字形（如 ⋮），换字符；eng.py 会按字形自动回退字体 |
| 画面闪烁 | 场景函数里用了无种子随机数，改为 `random.Random(固定种子)` 或预计算 |
| 成片偏小声 | final 已带 loudnorm（I=-16）；仍偏小检查 speech 是否被截断 |
| 字幕在代码里断开 | split_sub 只在中文标点断句；字幕里的代码尽量短 |
| edge-tts 失败 | 网络问题，tts.py 会重试 5 次；重跑只补缺失文件 |
| 磁盘不足 | 删旧项目的 seg/ 与 audio/；共享环境在 ~/.local/share/explainer-video |
