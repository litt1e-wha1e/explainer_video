import math, random, colorsys
import skia
from eng import *

TOKS = ["The", "cat", "sat", "on", "the"]
IDS = [464, 3797, 3332, 319, 262]
QC, KC, VC = YELLOW, BLUE, GREEN
GRAD = (255, 90, 90)
H12 = [tuple(int(255 * c) for c in colorsys.hsv_to_rgb(i / 12, 0.55, 1.0)) for i in range(12)]


class Ctx:
    def __init__(self, t, cues, durs, D):
        self.t, self.cues, self.durs, self.D = t, cues, durs, D

    def c(self, i):
        return self.cues[i] if i < len(self.cues) else self.D

    def d(self, i):
        return self.durs[i] if i < len(self.durs) else 1.0

    def m(self, i, f):
        return self.c(i) + self.d(i) * f

    def p(self, start, d=0.6, f=smooth):
        if d <= 0:
            return float(self.t >= start)
        return f((self.t - start) / d)

    def win(self, tin, tout, d=0.5):
        return self.p(tin, d) * (1 - self.p(tout, d))

    def phase(self, i, j=None, d=0.5):
        """从第 i 句开始出现，到第 j 句开始前淡出。"""
        tin = self.c(i) - 0.3 if i > 0 else 0.0
        tout = self.c(j) - 0.45 if j is not None else 1e9
        return self.p(tin, d) * (1 - self.p(tout, 0.4))


def heading(cv, S, s, color=WHITE, y=140, start=0.1, a=1.0, size=44):
    q = S.p(start, 0.6)
    text(cv, s, W / 2, y + (1 - ease_out(q)) * 20, size, color, q * a, bold=True)


def tok(cv, s, x, y, color=BLUE, a=1.0, p=1.0, size=34, w=None, h=None, glow=0, mono=False, fa=0.18, tcolor=WHITE):
    if a <= 0.003 or p <= 0:
        return 0
    q = ease_back(p)
    w = w or textw(s, size, mono=mono) + 36
    h = h or size * 1.8
    cv.save()
    cv.translate(x, y)
    cv.scale(0.5 + 0.5 * q, 0.5 + 0.5 * q)
    rect(cv, 0, 0, w, h, r=12, color=color, fill=color, fa=fa, a=a * clamp(p * 2), sw=2.5, glow=glow)
    text(cv, s, 0, 0, size, tcolor, a * clamp(p * 2), bold=not mono, mono=mono)
    cv.restore()
    return w


def mat(cv, x, y, rows, cols, cw, ch=None, vals=None, base=BLUE, a=1.0, p=1.0, show=False, fmt="{:.1f}",
        size=None, vmax=1.0, colorf=None, gap=3, outline=True, ocolor=None, sweep="diag", label=None, lsize=26,
        lcolor=None, cellf=None):
    """中心 (x,y) 的矩阵热力格。p 控制格子出现（斜向扫过）。返回 (左, 上, 宽, 高)。"""
    ch = ch or cw
    Wd = cols * (cw + gap) - gap
    Ht = rows * (ch + gap) - gap
    x0, y0 = x - Wd / 2, y - Ht / 2
    if a <= 0.003:
        return x0, y0, Wd, Ht
    if outline:
        oc = ocolor or mix(base, WHITE, 0.2)
        rect(cv, x, y, Wd + 14, Ht + 14, r=8, color=oc, a=a * 0.55, sw=2, draw=ease_out(clamp(p * 1.5)))
    n = rows + cols
    for i in range(rows):
        for j in range(cols):
            if sweep == "diag":
                q = clamp(p * (n + 3) - (i + j) - 1) if p < 1 else 1
            elif sweep == "row":
                q = clamp(p * (rows + 2) - i - 1) if p < 1 else 1
            else:
                q = clamp(p * (cols + 2) - j - 1) if p < 1 else 1
            if q <= 0:
                continue
            v = vals[i][j] if vals is not None else 0
            if colorf:
                c, ca = colorf(i, j, v)
            else:
                c, ca = val_color(v, base, vmax=vmax), 1.0
            if ca <= 0:
                continue
            cx, cy = x0 + j * (cw + gap) + cw / 2, y0 + i * (ch + gap) + ch / 2
            s = ease_back(q)
            rect(cv, cx, cy, cw * (0.5 + 0.5 * s), ch * (0.5 + 0.5 * s), r=min(cw, ch) * 0.18, color=None, fill=c,
                 fa=0.95, a=a * ca * clamp(q * 2), sw=0)
            if cellf:
                cellf(cv, i, j, cx, cy, a * ca * clamp(q * 2))
            elif show and q > 0.5:
                sv = fmt.format(v) if not isinstance(v, str) else v
                text(cv, sv, cx, cy, size or min(cw, ch) * 0.38, WHITE, a * ca * clamp((q - 0.5) * 2), bold=True)
    if label:
        text(cv, label, x, y + Ht / 2 + 34, lsize, lcolor or GREY, a * smooth(p * 2), mono=label.startswith("["))
    return x0, y0, Wd, Ht


def cell_xy(geo, i, j, cw, ch=None, gap=3):
    ch = ch or cw
    x0, y0 = geo[0], geo[1]
    return x0 + j * (cw + gap) + cw / 2, y0 + i * (ch + gap) + ch / 2


def rand_mat(r, c, seed, lo=-1, hi=1):
    rnd = random.Random(seed)
    return [[rnd.uniform(lo, hi) for _ in range(c)] for _ in range(r)]


def axes(cv, ox, oy, w, h, a=1.0, p=1.0, xl="", yl="", color=GREY, xneg=0, yneg=0):
    """坐标轴：原点 (ox,oy)，x 向右 w，y 向上 h；xneg/yneg 为负半轴长度。"""
    arrow(cv, ox - xneg, oy, ox + w, oy, color, a, 2.5, p=p, head=12)
    arrow(cv, ox, oy + yneg, ox, oy - h, color, a, 2.5, p=p, head=12)
    if xl:
        text(cv, xl, ox + w + 14, oy + 2, 26, color, a * smooth(p * 2 - 1), align="l")
    if yl:
        text(cv, yl, ox, oy - h - 26, 26, color, a * smooth(p * 2 - 1))


def curve(cv, f, xa, xb, ox, oy, sx, sy, color=BLUE, a=1.0, p=1.0, sw=4, glow=0, n=120, dash=None):
    pts = []
    for k in range(n + 1):
        xv = lerp(xa, xb, k / n)
        yv = f(xv)
        if yv is None:
            continue
        pts.append((ox + xv * sx, oy - yv * sy))
    if dash:
        for k in range(len(pts) - 1):
            pass
    poly(cv, pts, color, a, sw, p=p, glow=glow)
    return pts


def plus(cv, x, y, r=26, color=WHITE, a=1.0, p=1.0, glow=0):
    if a <= 0 or p <= 0:
        return
    q = ease_back(p)
    circle(cv, x, y, r * q, color, a * 0.15, glow=glow)
    circle(cv, x, y, r * q, color, a, fill=False, sw=2.5)
    line(cv, x - r * 0.5 * q, y, x + r * 0.5 * q, y, color, a, 3)
    line(cv, x, y - r * 0.5 * q, x, y + r * 0.5 * q, color, a, 3)


def flow_dots(cv, pts, t, color=BLUE, a=1.0, n=6, speed=0.5, r=6, glow=8, spacing=None):
    """沿折线流动的光点。t 为时间。"""
    if a <= 0.003 or len(pts) < 2:
        return
    segs = []
    L = 0
    for i in range(len(pts) - 1):
        l = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        segs.append(l)
        L += l
    for k in range(n):
        u = (t * speed + k / n) % 1.0
        d = u * L
        for i, l in enumerate(segs):
            if d <= l or i == len(segs) - 1:
                f = d / l if l else 0
                x = lerp(pts[i][0], pts[i + 1][0], clamp(f))
                y = lerp(pts[i][1], pts[i + 1][1], clamp(f))
                fade = math.sin(math.pi * u)
                circle(cv, x, y, r, color, a * fade, glow=glow)
                break
            d -= l


def dot_on(cv, pts, u, color=BLUE, a=1.0, r=9, glow=12):
    """在折线 pts 上比例 u 的位置画光点，返回坐标。"""
    if len(pts) < 2:
        return None
    segs = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    L = sum(segs)
    d = clamp(u) * L
    for i, l in enumerate(segs):
        if d <= l or i == len(segs) - 1:
            f = clamp(d / l if l else 0)
            x = lerp(pts[i][0], pts[i + 1][0], f)
            y = lerp(pts[i][1], pts[i + 1][1], f)
            if a > 0:
                circle(cv, x, y, r, color, a, glow=glow)
            return x, y
        d -= l


def bars(cv, x, y, vals, a=1.0, p=1.0, w=40, gap=14, sy=60, colors=None, base=BLUE, labels=None, lsize=24,
         show=False, fmt="{:.2f}", vsize=20, neg=RED, outline=False, hl=None):
    """以 (x, y) 为底部基线中心的柱状图（支持负值）。"""
    n = len(vals)
    tw = n * (w + gap) - gap
    x0 = x - tw / 2
    for i, v in enumerate(vals):
        q = ease_out(clamp(p * 1.6 - i / max(n, 1) * 0.6))
        if q <= 0:
            continue
        cx = x0 + i * (w + gap) + w / 2
        c = colors[i] if colors else (base if v >= 0 else neg)
        h = v * sy * q
        top = y - max(h, 0)
        rect(cv, cx, y - h / 2, w, abs(h) + 0.01, r=4, color=mix(c, WHITE, 0.3) if outline else None,
             fill=c, fa=0.85 if (hl is None or hl == i) else 0.35, a=a, sw=1.5 if outline else 0)
        if labels:
            text(cv, labels[i], cx, y + (28 if v >= 0 else -28 + 0) if False else y + 26, lsize, WHITE, a * q,
                 mono=False)
        if show and q > 0.7:
            ty = y - h - 18 if v >= 0 else y - h + 18
            text(cv, fmt.format(v), cx, ty, vsize, WHITE, a * clamp((q - 0.7) * 3), bold=True)
    return x0, tw


def node(cv, x, y, s, color=BLUE, a=1.0, p=1.0, r=46, size=30, glow=0, sub=None, subc=None):
    if a <= 0 or p <= 0:
        return
    q = ease_back(p)
    circle(cv, x, y, r * q, color, a * 0.16, glow=glow)
    circle(cv, x, y, r * q, color, a * clamp(p * 2), fill=False, sw=3)
    text(cv, s, x, y, size * (0.6 + 0.4 * q), WHITE, a * clamp(p * 2), bold=True)
    if sub:
        text(cv, sub, x, y + r + 26, 24, subc or GREY, a * clamp(p * 2 - 0.5))


def burst(cv, x, y, t0, t, color=YELLOW, n=18, R=120, a=1.0, seed=0):
    tt = (t - t0)
    if tt < 0 or tt > 1.2:
        return
    rnd = random.Random(seed)
    for i in range(n):
        ang = rnd.uniform(0, 6.283)
        sp = rnd.uniform(0.5, 1)
        r = R * sp * ease_out(clamp(tt / 1.0))
        circle(cv, x + math.cos(ang) * r, y + math.sin(ang) * r, rnd.uniform(2, 4.5), color,
               a * (1 - clamp(tt / 1.2)), glow=5)


def softmax(v, T=1.0):
    m = max(v)
    e = [math.exp((x - m) / T) for x in v]
    s = sum(e)
    return [x / s for x in e]


def cross(cv, x, y, s, color=RED, a=1.0, p=1.0, sw=6):
    line(cv, x - s, y - s, x + s, y + s, color, a, sw, p=clamp(p * 2), glow=6)
    line(cv, x + s, y - s, x - s, y + s, color, a, sw, p=clamp(p * 2 - 1), glow=6)


def check(cv, x, y, s, color=GREEN, a=1.0, p=1.0, sw=6):
    poly(cv, [(x - s, y), (x - s * 0.3, y + s * 0.7), (x + s, y - s * 0.8)], color, a, sw, p=p, glow=6)
