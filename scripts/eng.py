"""极简 2D 动画引擎：基于 skia，所有坐标以 1920x1080 为基准，元素多以中心点定位。"""
import math, random
import skia

W, H, FPS = 1920, 1080, 30

# ---------------------------------------------------------------- 颜色
BG = (7, 8, 13)
WHITE = (236, 239, 246)
GREY = (128, 134, 150)
DIM = (70, 75, 90)
BLUE = (88, 196, 221)
YELLOW = (255, 210, 80)
GREEN = (120, 205, 110)
RED = (252, 92, 80)
ORANGE = (255, 150, 60)
PURPLE = (170, 130, 255)
TEAL = (70, 225, 190)
PINK = (255, 105, 180)
HEADS = [BLUE, YELLOW, GREEN, PINK, PURPLE, ORANGE]


def argb(c, a=1.0):
    a = max(0.0, min(1.0, a))
    return skia.ColorSetARGB(int(a * 255), int(c[0]), int(c[1]), int(c[2]))


def mix(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(c1[i] + (c2[i] - c1[i]) * t for i in range(3))


# ---------------------------------------------------------------- 缓动
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_back(x):
    x = clamp(x)
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def lerp(a, b, t):
    return a + (b - a) * t


# ---------------------------------------------------------------- 字体
_tf = {
    "r": skia.Typeface.MakeFromFile("fonts/NotoSansCJKsc-Regular.otf"),
    "b": skia.Typeface.MakeFromFile("fonts/NotoSansCJKsc-Bold.otf"),
    "m": skia.Typeface.MakeFromFile("fonts/DejaVuSansMono.ttf"),
    "mb": skia.Typeface.MakeFromFile("fonts/DejaVuSansMono-Bold.ttf"),
}
_fonts = {}
_has = {}


def font(kind, size):
    k = (kind, int(size * 4))
    f = _fonts.get(k)
    if f is None:
        f = skia.Font(_tf[kind], size)
        f.setSubpixel(True)
        f.setEdging(skia.Font.Edging.kAntiAlias)
        _fonts[k] = f
    return f


def has_glyph(kind, ch):
    k = (kind, ch)
    v = _has.get(k)
    if v is None:
        v = font(kind, 20).unicharToGlyph(ord(ch)) != 0
        _has[k] = v
    return v


def runs(s, kind):
    """按字形可用性切分成 (文本, 字体类型) 段，实现字体回退。"""
    fb = ["m", "r"] if kind in ("r", "b") else ["r", "m"]
    out = []
    for ch in s:
        use = kind
        if not has_glyph(kind, ch):
            for f2 in fb:
                if has_glyph(f2, ch):
                    use = f2
                    break
        if out and out[-1][1] == use:
            out[-1][0] += ch
        else:
            out.append([ch, use])
    return out


def kind_of(bold, mono):
    return ("mb" if bold else "m") if mono else ("b" if bold else "r")


def textw(s, size, bold=False, mono=False):
    return sum(font(k, size).measureText(t) for t, k in runs(s, kind_of(bold, mono)))


def _paint(c, a, stroke=None, blur=0):
    p = skia.Paint(AntiAlias=True, Color=argb(c, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeJoin(skia.Paint.kRound_Join)
        p.setStrokeCap(skia.Paint.kRound_Cap)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


def text(cv, s, x, y, size=40, color=WHITE, a=1.0, align="c", bold=False, mono=False,
         glow=0, outline=0, ocolor=(0, 0, 0)):
    """在 (x,y) 绘制文字，y 为垂直中心。align: l/c/r。"""
    if a <= 0.003 or not s:
        return
    k0 = kind_of(bold, mono)
    rs = runs(s, k0)
    widths = [font(k, size).measureText(t) for t, k in rs]
    tw = sum(widths)
    x0 = x - tw / 2 if align == "c" else (x - tw if align == "r" else x)
    m = font("r", size).getMetrics()
    base = y - (m.fAscent + m.fDescent) / 2
    passes = []
    if glow:
        passes.append(_paint(color, a * 0.85, blur=glow))
    if outline:
        passes.append(_paint(ocolor, a * 0.9, stroke=outline))
    passes.append(_paint(color, a))
    for p in passes:
        xx = x0
        for (t, k), w in zip(rs, widths):
            cv.drawString(t, xx, base, font(k, size), p)
            xx += w
    return tw


def typer(cv, s, x, y, p, size=40, color=WHITE, a=1.0, align="l", cursor=True, **kw):
    n = int(round(len(s) * clamp(p)))
    shown = s[:n]
    tw = text(cv, shown, x, y, size, color, a, align, **kw) or 0
    if cursor and 0 < p < 1:
        if align == "l":
            cx = x + tw
        elif align == "c":
            full = textw(shown, size, kw.get("bold", False), kw.get("mono", False))
            cx = x + full / 2
        else:
            cx = x
        rect(cv, cx + 4, y, 3, size * 0.9, color=color, fill=color, a=a, sw=0)


# ---------------------------------------------------------------- 形状
def _trim(path, p):
    if p >= 0.999:
        return None
    L = skia.PathMeasure(path, False).getLength() or 1
    return skia.DashPathEffect.Make([L * p + 0.01, L * 2], 0)


def rect(cv, x, y, w, h, r=0, color=WHITE, fill=None, a=1.0, sw=3, draw=1.0, glow=0, fa=None):
    """中心 (x,y) 的圆角矩形。draw 为描边进度（勾勒动画）。fill 为填充颜色。"""
    if a <= 0.003:
        return
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - w / 2, y - h / 2, w, h), r, r)
    if fill is not None:
        fa_ = (0.18 if fa is None else fa) * a * smooth(draw * 1.4 - 0.4 if sw else 1)
        cv.drawRRect(rr, _paint(fill, fa_))
    if sw and color is not None and draw > 0:
        path = skia.Path()
        path.addRRect(rr)
        if glow:
            pg = _paint(color, a * 0.7, stroke=sw * 2, blur=glow)
            pe = _trim(path, draw)
            if pe:
                pg.setPathEffect(pe)
            cv.drawPath(path, pg)
        ps = _paint(color, a, stroke=sw)
        pe = _trim(path, draw)
        if pe:
            ps.setPathEffect(pe)
        cv.drawPath(path, ps)


def circle(cv, x, y, r, color=WHITE, a=1.0, fill=True, sw=3, glow=0):
    if a <= 0.003 or r <= 0:
        return
    if glow:
        cv.drawCircle(x, y, r * 1.2, _paint(color, a * 0.6, blur=glow))
    cv.drawCircle(x, y, r, _paint(color, a, stroke=None if fill else sw))


def line(cv, x1, y1, x2, y2, color=WHITE, a=1.0, sw=3, p=1.0, dash=None, glow=0, phase=0):
    if a <= 0.003 or p <= 0:
        return
    xe, ye = lerp(x1, x2, p), lerp(y1, y2, p)
    pt = _paint(color, a, stroke=sw)
    if dash:
        pt.setPathEffect(skia.DashPathEffect.Make(dash, phase))
    if glow:
        pg = _paint(color, a * 0.6, stroke=sw * 2.5, blur=glow)
        cv.drawLine(x1, y1, xe, ye, pg)
    cv.drawLine(x1, y1, xe, ye, pt)


def arrow(cv, x1, y1, x2, y2, color=WHITE, a=1.0, sw=4, p=1.0, head=16, glow=0, dash=None):
    if a <= 0.003 or p <= 0:
        return
    xe, ye = lerp(x1, x2, p), lerp(y1, y2, p)
    ang = math.atan2(ye - y1, xe - x1)
    L = math.hypot(xe - x1, ye - y1)
    hl = min(head, L * 0.6)
    bx, by = xe - math.cos(ang) * hl * 0.8, ye - math.sin(ang) * hl * 0.8
    line(cv, x1, y1, bx, by, color, a, sw, glow=glow, dash=dash)
    path = skia.Path()
    path.moveTo(xe, ye)
    path.lineTo(xe - math.cos(ang - 0.45) * hl, ye - math.sin(ang - 0.45) * hl)
    path.lineTo(xe - math.cos(ang + 0.45) * hl, ye - math.sin(ang + 0.45) * hl)
    path.close()
    cv.drawPath(path, _paint(color, a))


def bezier(cv, pts, color=WHITE, a=1.0, sw=3, p=1.0, dash=None, phase=0, glow=0, head=0):
    """三次贝塞尔：pts=[(x0,y0),(c1),(c2),(x1,y1)]"""
    if a <= 0.003 or p <= 0:
        return
    path = skia.Path()
    path.moveTo(*pts[0])
    path.cubicTo(*pts[1], *pts[2], *pts[3])
    L = skia.PathMeasure(path, False).getLength() or 1
    if p < 0.999 or dash:
        effs = []
        if dash:
            effs.append(skia.DashPathEffect.Make(dash, phase))
        if p < 0.999:
            effs.append(skia.DashPathEffect.Make([L * p + 0.01, L * 2], 0))
        pe = effs[0] if len(effs) == 1 else skia.PathEffect.MakeCompose(effs[0], effs[1])
    else:
        pe = None
    if glow:
        pg = _paint(color, a * 0.6, stroke=sw * 2.5, blur=glow)
        if pe:
            pg.setPathEffect(pe)
        cv.drawPath(path, pg)
    ps = _paint(color, a, stroke=sw)
    if pe:
        ps.setPathEffect(pe)
    cv.drawPath(path, ps)
    if head and p > 0.05:
        pm = skia.PathMeasure(path, False)
        pos, tan = pm.getPosTan(L * p)
        ang = math.atan2(tan.y(), tan.x())
        hp = skia.Path()
        hp.moveTo(pos.x(), pos.y())
        hp.lineTo(pos.x() - math.cos(ang - 0.45) * head, pos.y() - math.sin(ang - 0.45) * head)
        hp.lineTo(pos.x() - math.cos(ang + 0.45) * head, pos.y() - math.sin(ang + 0.45) * head)
        hp.close()
        cv.drawPath(hp, _paint(color, a))


def bez_point(pts, t):
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = pts
    u = 1 - t
    return (u**3 * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t**3 * x3,
            u**3 * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t**3 * y3)


def poly(cv, pts, color=WHITE, a=1.0, sw=3, p=1.0, fill=None, fa=0.2, glow=0, closed=False):
    if a <= 0.003 or len(pts) < 2:
        return
    path = skia.Path()
    path.moveTo(*pts[0])
    for q in pts[1:]:
        path.lineTo(*q)
    if closed:
        path.close()
    if fill is not None:
        cv.drawPath(path, _paint(fill, fa * a))
    pe = _trim(path, p)
    if glow:
        pg = _paint(color, a * 0.6, stroke=sw * 2.5, blur=glow)
        if pe:
            pg.setPathEffect(pe)
        cv.drawPath(path, pg)
    ps = _paint(color, a, stroke=sw)
    if pe:
        ps.setPathEffect(pe)
    cv.drawPath(path, ps)


# ---------------------------------------------------------------- 复合元素
def val_color(v, base=BLUE, neg=RED, vmax=1.0):
    t = clamp(abs(v) / vmax)
    return mix((25, 28, 40), base if v >= 0 else neg, 0.25 + 0.75 * t)


def vec(cv, x, y, vals, cell=40, base=BLUE, a=1.0, vertical=False, p=1.0, show=True,
        size=None, vmax=1.0, fmt="{:.1f}", label=None, lcolor=None, gap=4, glow=0, colors=None):
    """一个向量：一排（或一列）彩色小方格，中心在 (x,y)。p 控制逐格出现。"""
    n = len(vals)
    step = cell + gap
    total = n * step - gap
    size = size or cell * 0.36
    for i, v in enumerate(vals):
        q = clamp(p * n - i)
        if q <= 0:
            continue
        q = ease_back(q)
        if vertical:
            cx, cy = x, y - total / 2 + i * step + cell / 2
        else:
            cx, cy = x - total / 2 + i * step + cell / 2, y
        c = colors[i] if colors else val_color(v, base, vmax=vmax)
        s = cell * (0.4 + 0.6 * q)
        rect(cv, cx, cy, s, s, r=6, color=mix(c, WHITE, 0.25), fill=c, fa=0.95, a=a * clamp(q * 2), sw=1.5, glow=glow)
        if show and q > 0.6:
            sv = fmt.format(v) if not isinstance(v, str) else v
            text(cv, sv, cx, cy, size, WHITE, a * clamp((q - 0.6) * 3), bold=True)
    if label and p > 0:
        if vertical:
            text(cv, label, x, y + total / 2 + 30, 26, lcolor or GREY, a * smooth(p * 2))
        else:
            text(cv, label, x, y + cell / 2 + 28, 26, lcolor or GREY, a * smooth(p * 2))
    return total


def box(cv, x, y, w, h, label="", sub="", color=BLUE, a=1.0, p=1.0, size=34, subsize=24,
        glow=0, r=16, fa=0.14, bold=True, sw=3):
    """带标题的框：勾勒描边 + 填充 + 文字淡入。"""
    if a <= 0.003 or p <= 0:
        return
    rect(cv, x, y, w, h, r=r, color=color, fill=color, fa=fa, a=a, sw=sw, draw=ease_out(p), glow=glow)
    ta = a * smooth(p * 2 - 0.6)
    if sub:
        text(cv, label, x, y - h * 0.15, size, WHITE, ta, bold=bold)
        text(cv, sub, x, y + h * 0.24, subsize, mix(color, WHITE, 0.4), ta, mono=sub.startswith("["))
    else:
        text(cv, label, x, y, size, WHITE, ta, bold=bold)


def chip(cv, x, y, s, color=BLUE, a=1.0, size=28, p=1.0, mono=False, padx=22, h=None, glow=0):
    if a <= 0.003 or p <= 0:
        return
    q = ease_back(p)
    w = textw(s, size, mono=mono) + padx * 2
    h = h or size * 1.75
    cv.save()
    cv.translate(x, y)
    cv.scale(0.6 + 0.4 * q, 0.6 + 0.4 * q)
    rect(cv, 0, 0, w, h, r=h / 2, color=color, fill=color, fa=0.16, a=a * clamp(p * 2), sw=2, glow=glow)
    text(cv, s, 0, 0, size, WHITE, a * clamp(p * 2), mono=mono)
    cv.restore()
    return w


# ---------------------------------------------------------------- 代码面板
import re as _re
KW = set("def class return for in if else elif None import from as self lambda with not and or True False".split())
_tok = _re.compile(r"(#.*$)|('[^']*'|\"[^\"]*\")|(\b\d+(?:\.\d+)?(?:e-?\d+)?\b)|([A-Za-z_][A-Za-z_0-9]*)|(\s+)|(.)")


def code_line(cv, s, x, y, size=24, a=1.0):
    xx = x
    f = font("m", size)
    m = f.getMetrics()
    base = y - (m.fAscent + m.fDescent) / 2
    for mt in _tok.finditer(s):
        t = mt.group(0)
        if mt.group(1):
            c = (110, 118, 135)
        elif mt.group(2):
            c = (152, 211, 125)
        elif mt.group(3):
            c = (247, 160, 90)
        elif mt.group(4):
            if t in KW:
                c = (199, 146, 234)
            elif s[mt.end():mt.end() + 1] == "(":
                c = (110, 190, 255)
            else:
                c = (225, 228, 236)
        else:
            c = (190, 196, 210)
        if not t.isspace():
            cv.drawString(t, xx, base, f, _paint(c, a))
        xx += f.measureText(t)


def code(cv, lines, x, y, size=24, a=1.0, hl=None, title="gpt.py", p=1.0, w=None):
    """代码面板，(x,y) 为左上角。hl=(行号, 强度)。p 控制逐行打出。"""
    if a <= 0.003:
        return
    lh = size * 1.55
    w = w or max(font("m", size).measureText(l) for l in lines) + 60
    h = lh * len(lines) + 70
    q = smooth(p * 3)
    rect(cv, x + w / 2, y + h / 2, w, h, r=14, color=(60, 66, 84), fill=(18, 20, 30), fa=0.92, a=a * q, sw=1.5)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        circle(cv, x + 22 + i * 22, y + 20, 6, c, a * q)
    text(cv, title, x + w - 20, y + 20, 18, GREY, a * q, align="r", mono=True)
    n = len(lines)
    for i, l in enumerate(lines):
        li = clamp(p * n - i)
        if li <= 0:
            continue
        yy = y + 52 + lh * i + lh / 2
        if hl is not None:
            hs = hl if isinstance(hl, (list, tuple)) and hl and isinstance(hl[0], tuple) else [hl]
            for hli, hla in hs:
                if hli == i and hla > 0:
                    rect(cv, x + w / 2, yy, w - 16, lh, r=6, color=None, fill=YELLOW, fa=0.13 * hla, a=a, sw=0)
                    rect(cv, x + 10, yy, 4, lh, color=None, fill=YELLOW, fa=hla, a=a, sw=0)
        sub = l[:int(len(l) * clamp(li * 1.0))]
        code_line(cv, sub, x + 24, yy, size, a * clamp(li * 3))
    return w, h


# ---------------------------------------------------------------- 背景
class Background:
    def __init__(self):
        surf = skia.Surface(W, H)
        c = surf.getCanvas()
        c.clear(argb(BG))
        gp = _paint((90, 110, 160), 0.05, stroke=1)
        for gx in range(0, W + 1, 60):
            c.drawLine(gx, 0, gx, H, gp)
        for gy in range(0, H + 1, 60):
            c.drawLine(0, gy, W, gy, gp)
        sh = skia.GradientShader.MakeRadial(skia.Point(W / 2, H / 2), W * 0.75,
                                            [argb((0, 0, 0), 0), argb((0, 0, 0), 0.85)])
        c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))
        sh2 = skia.GradientShader.MakeRadial(skia.Point(W * 0.5, H * 0.42), 700,
                                             [argb((40, 70, 140), 0.10), argb((40, 70, 140), 0)])
        c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh2))
        self.img = surf.makeImageSnapshot()
        rnd = random.Random(7)
        self.parts = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(0.6, 2.2), rnd.uniform(-8, 8),
                       rnd.uniform(-14, -3), rnd.uniform(0, 6.28)) for _ in range(70)]

    def draw(self, cv, t):
        cv.drawImage(self.img, 0, 0)
        for x, y, r, vx, vy, ph in self.parts:
            px = (x + vx * t) % W
            py = (y + vy * t) % H
            a = 0.10 + 0.10 * math.sin(t * 0.8 + ph)
            cv.drawCircle(px, py, r, _paint((150, 180, 255), a))
