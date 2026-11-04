# 绘图引擎 API（eng.py + common.py）

画布固定 1920×1080、30fps。**坐标几乎都以元素中心为准**（`code()` 例外，用左上角）。
`from common import *` 会把 eng.py 的东西一起引入。

## 目录
1. 安全区与版式
2. 时间：Ctx
3. 颜色与缓动
4. 基础图元（eng.py）
5. 复合元素（eng.py）
6. 常用组件（common.py）
7. 场景函数的写法套路

---

## 1. 安全区与版式

| 区域 | y 范围 | 说明 |
|---|---|---|
| 左上章节标签 / 右上 TAG | ≈ 62 | make.py 的 overlays 自动绘制，不要在这里放内容 |
| heading（场景标题） | 140 | `heading()` 默认 y=140 |
| 主内容区 | 200 ~ 900 | |
| 字幕 | 985 | 46px 粗体 + 描边，内容别低于 ~920 |
| 进度条 | 1075 | 自动绘制 |

水平方向留 ≥ 80px 边距。文字超出右边界是最常见的版式 bug，长文本用 `textw()` 量一下。

## 2. 时间：Ctx（每个场景函数的参数 `S`）

- `S.t`：场景内时间（秒）
- `S.c(i)`：第 i 句旁白**开口时刻**（i 超出范围返回场景总长）
- `S.d(i)`：第 i 句时长；`S.m(i, f)`：第 i 句说到 f（0~1）比例的时刻
- `S.p(start, d=0.6, f=smooth)`：从 start 开始、持续 d 秒的 0→1 进度
- `S.win(tin, tout, d=0.5)`：tin 淡入、tout 淡出的窗口
- `S.phase(i, j=None)`：**从第 i 句开始出现，到第 j 句前淡出**。这是划分画面阶段的主力：
  ```python
  aA = S.phase(0, 3)   # 第 0~2 句
  if aA > 0: ...       # 全部元素的 alpha 乘 aA
  aB = S.phase(3)      # 第 3 句到场景结束
  ```
场景整体的淡入淡出、轻微缩放由 make.py 统一处理，场景内不用管。

## 3. 颜色与缓动

颜色（RGB 元组）：`BG WHITE GREY DIM BLUE YELLOW GREEN RED ORANGE PURPLE TEAL PINK`，`HEADS`（6 色）；common.py 另有 `H12`（12 色）、`QC/KC/VC`（Q/K/V 黄/蓝/绿）、`GRAD`（梯度红）。
`mix(c1, c2, t)` 混色；`val_color(v, base, neg, vmax)` 按数值上色（正 base / 负 neg）。
缓动：`smooth` `ease_out` `ease_back`（回弹，用于弹出）`clamp` `lerp`。

## 4. 基础图元（eng.py）

- `text(cv, s, x, y, size, color, a, align="c"|"l"|"r", bold, mono, glow, outline)`：y 是垂直中心；自动中英文字体回退
- `textw(s, size, bold, mono)`：量宽度
- `typer(cv, s, x, y, p, ...)`：打字机效果，p=0~1
- `rect(cv, x, y, w, h, r, color, fill, a, sw, draw, glow, fa)`：`draw` 0~1 = 描边勾勒动画；`fill`+`fa` 填充
- `circle` `line(…, p, dash, glow)` `arrow(…, p, head)` `poly(pts, …, p, closed, fill)`
- `bezier(cv, [(x0,y0),c1,c2,(x1,y1)], …, p, dash, phase, head)`：`phase=-t*30` 做流动虚线；`bez_point(pts, t)` 取曲线上的点

## 5. 复合元素（eng.py）

- `vec(cv, x, y, vals, cell, base, a, vertical, p, show, fmt, label)`：向量方格，p 控制逐格弹出
- `box(cv, x, y, w, h, label, sub, color, a, p, size)`：带标题的框（`sub` 以 `[` 开头时用等宽）
- `chip(cv, x, y, s, color, a, size, p, mono, glow)`：胶囊标签，自动宽度
- `code(cv, lines, x, y, size, a, hl=(行号, 强度) 或 [(行,强度),…] 或 None, title, p, w)`：代码面板，左上角定位，语法高亮，p 逐行打出。**hl 不能传空列表**，没有高亮时传 None

## 6. 常用组件（common.py）

- `heading(cv, S, s, color, y=140, start, a, size)`：场景标题（带上浮淡入）
- `tok(cv, s, x, y, color, a, p, size, w, mono, glow)`：token / 单词方块（回弹弹出）
- `mat(cv, x, y, rows, cols, cw, ch, vals, base, a, p, show, fmt, colorf, cellf, sweep, label)`：热力矩阵，返回 geo=(x0,y0,w,h)；`colorf(i,j,v)->(color, alpha)` 自定义每格颜色；`cellf(cv,i,j,cx,cy,a)` 自定义格内绘制；`cell_xy(geo, i, j, cw, ch)` 取格子中心
- `rand_mat(r, c, seed)`：固定种子的随机矩阵（保证每帧一致！不要在场景函数里用不带种子的 random）
- `bars(cv, x, y_baseline, vals, a, p, w, gap, sy, colors, base, neg, show, fmt)`：柱状图（支持负值），返回 (x0, 总宽)
- `axes(cv, ox, oy, w, h, a, p, xl, yl, xneg, yneg)` + `curve(cv, f, xa, xb, ox, oy, sx, sy, color, a, p)`：坐标系与函数曲线（p 画线进度）
- `node`（圆形节点）`plus`（⊕）`cross`（红叉）`check`（绿勾）`burst`（粒子爆开）
- `flow_dots(cv, pts, t, …)`：沿折线循环流动的光点；`dot_on(cv, pts, u, …)`：折线上比例 u 处的光点
- `softmax(v, T)`

## 7. 场景函数的写法套路

```python
def s_xxx(cv, S):
    t = S.t
    aA = S.phase(0, 2)                      # 阶段 A：第 0、1 句
    if aA > 0:
        heading(cv, S, "标题", a=aA)
        for k in range(n):                  # 依次弹出：起点错开
            tok(cv, ..., aA, S.p(0.4 + k * 0.15, 0.5), ...)
        q1 = S.p(S.c(1), 0.6)               # 第 1 句开口时出现的强调
        if q1 > 0: ...
    aB = S.phase(2)
    if aB > 0:
        heading(cv, S, "标题 B", a=aB, start=S.c(2))
        # 逐步演示的状态机：u = (t - 起点) / 时长 * 步数，k = int(u)，f = u - k
```

要点：
- **一切必须是 t 的纯函数**：每帧独立重绘，随机数一律用固定种子（`random.Random(seed)`），否则画面会闪。
- 动画与旁白对齐靠 `S.c(i)` / `S.m(i, f)`，不要写死秒数（旁白重新生成后时长会变）。
- 动画位移用 `lerp(a, b, ease_out(q))`，弹出用 `ease_back`。
- 同一区域的两个阶段要用 phase 互斥，否则画面会重叠。
- 数值演示（例如算法的每一步）尽量**用真实代码算出来**再画，不要手编数字。
