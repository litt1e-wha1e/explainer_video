from common import *   # 引入 eng.py 的全部绘图工具 + Ctx / heading / tok / mat / bars / axes / curve / node …


def s_intro(cv, S):
    """S.t = 场景内时间；S.c(i) = 第 i 句开口时刻；S.d(i) = 第 i 句时长；S.m(i, f) = 第 i 句说到 f 比例处。"""
    q = S.p(0.2, 0.8)                                  # 0.2s 起用 0.8s 淡入
    text(cv, "标题", 960, 420, 120, BLUE, q, bold=True, glow=24)
    text(cv, "副标题", 960, 560, 44, WHITE, S.p(0.8, 0.6))
    q1 = S.p(S.c(1), 0.6)                              # 第 2 句开始时出现
    chip(cv, 960, 700, "3 × 4 = 12", YELLOW, q1, 34, p=q1, mono=True, glow=8)


def s_demo(cv, S):
    aA = S.phase(0, 1)                                 # 阶段 A：第 0 句出现，第 1 句前淡出
    if aA > 0:
        heading(cv, S, "阶段 A：逐个弹出", a=aA)
        for k in range(5):
            tok(cv, str(k), 560 + k * 200, 480, BLUE, aA, S.p(0.5 + k * 0.2, 0.5), 40, w=120, mono=True)
    aB = S.phase(1)                                    # 阶段 B：第 1 句起
    if aB > 0:
        heading(cv, S, "阶段 B：矩阵 + 柱状图", a=aB, start=S.c(1))
        mat(cv, 600, 520, 5, 5, 60, 60, rand_mat(5, 5, 1), a=aB, p=S.p(S.c(1) + 0.2, 1.0), show=True)
        bars(cv, 1350, 700, [0.5, 1.2, 2.0, 0.8, 1.6], aB, S.p(S.c(1) + 0.6, 1.0), w=60, gap=24, sy=120,
             show=True, fmt="{:.1f}")
