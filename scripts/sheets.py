# 为每个场景生成联系表：每句话的 85% 处取一帧，每 4 帧一张
import sys, numpy as np, skia
from make import TL, render, W, H
ids = sys.argv[1:] or [x["id"] for x in TL]
import os; os.makedirs("sheets", exist_ok=True)
for sc in TL:
    if sc["id"] not in ids: continue
    times = []
    for i, (c, d) in enumerate(zip(sc["cues"], sc["durs"])):
        times.append((f"c{i}", c + d * 0.85))
    times.append(("end", sc["dur"] - 0.7))
    for b in range(0, len(times), 4):
        big = skia.Surface(W, H); bc = big.getCanvas(); bc.clear(skia.ColorBLACK)
        for k, (lab, lt) in enumerate(times[b:b+4]):
            arr = np.zeros((H, W, 4), np.uint8); s = skia.Surface(arr)
            with s as cv: render(cv, sc["start"] + lt)
            x, y = (k % 2) * W / 2, (k // 2) * H / 2
            bc.drawImageRect(s.makeImageSnapshot(), skia.Rect.MakeXYWH(x, y, W / 2, H / 2), skia.SamplingOptions(skia.FilterMode.kLinear))
            bc.drawString(f"{sc['id']} {lab} {lt:.1f}", x + 10, y + 30, skia.Font(skia.Typeface.MakeFromFile("fonts/DejaVuSansMono.ttf"), 24), skia.Paint(Color=skia.ColorMAGENTA))
        big.makeImageSnapshot().save(f"sheets/{sc['id']}_{b//4}.png", skia.kPNG)
    print("sheet", sc["id"], flush=True)
