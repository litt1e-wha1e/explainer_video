import sys, traceback, numpy as np, skia
from make import TL, render, W, H
arr = np.zeros((H, W, 4), np.uint8); s = skia.Surface(arr); cv = s.getCanvas()
ids = sys.argv[1:] or [x["id"] for x in TL]
for sc in TL:
    if sc["id"] not in ids: continue
    n = int(sc["dur"] / 0.25)
    for k in range(n):
        T = sc["start"] + k * 0.25
        try:
            cv.clear(skia.ColorBLACK); render(cv, T)
        except Exception as e:
            print(sc["id"], round(k*0.25,2), repr(e)); traceback.print_exc(limit=-2); break
    else:
        print("ok", sc["id"], flush=True)
