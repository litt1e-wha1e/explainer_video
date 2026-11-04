import os, sys, json, math, re, subprocess, wave, random
import numpy as np
import skia
import imageio_ffmpeg
from eng import *
from script import SCRIPT
from scenes import SCENES, Ctx
import config

FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 24000
LEAD = {SCRIPT[0][0]: getattr(config, "LEAD_FIRST", 1.2)}
GAP, TAIL = 0.35, 1.0

meta = json.load(open("audio/meta.json"))
by = {}
for m in meta:
    by.setdefault(m["scene"], []).append(m)


def split_sub(s, limit=21):
    # 只在中文标点处断句（英文逗号常出现在代码/元组里，不能断）
    parts = re.findall(r"[^，。；：？！;]+[，。；：？！;]?", s)
    out = []
    for p in parts:
        if out and len(out[-1]) + len(p) <= limit:
            out[-1] += p
        else:
            out.append(p)
    final = []
    for p in out:
        while len(p) > limit + 6:
            k = limit
            for j in range(limit, max(limit - 10, 4), -1):
                a, b = p[j - 1], p[j]
                depth = p[:j].count("(") - p[:j].count(")") + p[:j].count("[") - p[:j].count("]")
                if depth == 0 and not (re.match(r"[\w\[\(\.'\"\-]", a, re.A) and re.match(r"[\w\]\)\.'\",\-]", b, re.A)):
                    k = j
                    break
            final.append(p[:k].rstrip())
            p = p[k:].lstrip()
        final.append(p)
    return [x for x in final if x.strip()]


# ------------------------------------------------------------- 时间线
TL = []
cur = 0.0
SUBS = []
for sid, label, sents in SCRIPT:
    ms = by[sid]
    st = cur
    lt = LEAD.get(sid, 0.7)
    cues, durs = [], []
    for m in ms:
        cues.append(lt)
        durs.append(m["dur"])
        chunks = split_sub(m["sub"])
        tot = sum(len(c) for c in chunks)
        tt = st + lt
        for c in chunks:
            d = m["dur"] * len(c) / tot
            SUBS.append((tt, tt + d, c.rstrip("，。；：,;")))
            tt += d
        lt += m["dur"] + GAP
    D = lt - GAP + TAIL
    TL.append(dict(id=sid, label=label, start=st, dur=D, cues=cues, durs=durs))
    cur += D
TOTAL = cur


# ------------------------------------------------------------- 音频
def load_mp3(p):
    raw = subprocess.run([FF, "-v", "quiet", "-i", p, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def build_audio(path="audio/mix.wav"):
    N = int((TOTAL + 1) * SR)
    speech = np.zeros(N, np.float32)
    for sc in TL:
        for m, c in zip(by[sc["id"]], sc["cues"]):
            x = load_mp3(m["path"])
            i = int((sc["start"] + c) * SR)
            speech[i:i + len(x)] += x[:N - i]
    # 背景氛围音：缓慢变化的和弦铺底
    chords = [[110.0, 164.81, 220.0, 261.63], [87.31, 130.81, 174.61, 220.0],
              [130.81, 196.0, 261.63, 329.63], [98.0, 146.83, 196.0, 246.94]]
    seg = 8.0
    pad = np.zeros(N, np.float32)
    for k in range(int(TOTAL / seg) + 2):
        t0 = k * seg
        i0, i1 = int(max(t0 - 2, 0) * SR), int(min(t0 + seg + 2, TOTAL + 1) * SR)
        if i0 >= N:
            break
        tt = np.arange(i0, i1) / SR
        env = np.clip(np.minimum((tt - (t0 - 2)) / 3, ((t0 + seg + 2) - tt) / 3), 0, 1)
        env = env * env * (3 - 2 * env)
        sig = np.zeros_like(tt)
        for f in chords[k % 4]:
            sig += np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt + 0.5)
            sig += 0.5 * np.sin(2 * np.pi * f * 1.003 * tt)
        pad[i0:i1] += (sig * env * (0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * tt))).astype(np.float32)
    pad /= np.abs(pad).max() + 1e-6
    # 侧链压低：有人声时音乐降低
    k5 = SR // 5
    cs = np.concatenate([[0.0], np.cumsum(np.abs(speech), dtype=np.float64)])
    idx = np.arange(N)
    lo = np.clip(idx - k5 // 2, 0, N); hi = np.clip(idx + k5 // 2, 0, N)
    envs = ((cs[hi] - cs[lo]) / k5).astype(np.float32)
    del cs, idx, lo, hi
    duck = 1 - 0.55 * np.clip(envs * 12, 0, 1)
    music = pad * 0.055 * duck
    t = np.arange(N, dtype=np.float32) / SR
    fade = np.clip(np.minimum(t / 2.0, (TOTAL - t) / 3.0), 0, 1)
    del t
    music *= fade
    # 转场 whoosh
    rnd = np.random.default_rng(0)
    for sc in TL[1:]:
        i = int((sc["start"] - 0.35) * SR)
        L = int(0.8 * SR)
        if i < 0 or i + L > N:
            continue
        noise = rnd.standard_normal(L).astype(np.float32)
        k = np.linspace(0, 1, L)
        # 简单低通：滑动平均，窗口随时间变小 → 扫频效果
        out = np.zeros(L, np.float32)
        cs = np.cumsum(np.concatenate([[0], noise]))
        for j0 in range(0, L, 400):
            win = int(lerp(60, 6, k[j0]))
            j1 = min(j0 + 400, L)
            idx = np.arange(j0, j1)
            lo = np.clip(idx - win, 0, L)
            out[j0:j1] = (cs[idx] - cs[lo]) / win
        env = np.sin(np.pi * k) ** 2
        music[i:i + L] += out * env * 0.05
    mixd = speech * 0.95 + music
    mixd = np.clip(mixd, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mixd * 32767).astype(np.int16).tobytes())
    print("audio", TOTAL)


# ------------------------------------------------------------- 画面
bg = Background()


def subtitle(cv, T):
    for a, b, s in SUBS:
        if a - 0.1 <= T < b + 0.12:
            al = clamp((T - (a - 0.1)) / 0.12) * clamp((b + 0.12 - T) / 0.12)
            text(cv, s, W / 2, 985, 46, WHITE, al, bold=True, outline=8, ocolor=(0, 0, 0))
            break


def overlays(cv, sc, lt, T):
    if sc["id"] != TL[0]["id"]:
        p = ease_out(clamp(lt / 0.7))
        x = 70 - (1 - p) * 60
        rect(cv, x, 62, 6, 34, r=3, color=None, fill=BLUE, fa=p, sw=0)
        text(cv, sc["label"], x + 22, 62, 28, WHITE, p * 0.9, align="l", bold=True)
    text(cv, config.TAG, W - 70, 62, 22, GREY, 0.6, align="r")
    # 进度条
    pr = T / TOTAL
    rect(cv, W / 2, H - 5, W, 4, color=None, fill=(40, 44, 60), fa=1, sw=0)
    rect(cv, W * pr / 2, H - 5, W * pr, 4, color=None, fill=BLUE, fa=1, sw=0)
    for s in TL[1:]:
        x = s["start"] / TOTAL * W
        rect(cv, x, H - 5, 3, 8, color=None, fill=(10, 10, 14), fa=1, sw=0)
    subtitle(cv, T)


def scene_at(T):
    for sc in TL:
        if T < sc["start"] + sc["dur"]:
            return sc
    return TL[-1]


def render(cv, T):
    sc = scene_at(T)
    lt = T - sc["start"]
    bg.draw(cv, T)
    fi = smooth(lt / 0.5)
    fo = smooth((sc["dur"] - lt) / 0.45)
    a = min(fi, fo)
    if a > 0.002:
        cv.save()
        s = 0.97 + 0.03 * ease_out(clamp(lt / 0.8))
        cv.translate(W / 2, H / 2)
        cv.scale(s, s)
        cv.translate(-W / 2, -H / 2)
        if a < 0.999:
            cv.saveLayerAlpha(None, int(a * 255))
        SCENES[sc["id"]](cv, Ctx(lt, sc["cues"], sc["durs"], sc["dur"]))
        if a < 0.999:
            cv.restore()
        cv.restore()
    overlays(cv, sc, lt, T)


def still(T, path):
    arr = np.zeros((H, W, 4), np.uint8)
    surf = skia.Surface(arr)
    with surf as cv:
        render(cv, T)
    surf.makeImageSnapshot().save(path, skia.kPNG)


def render_segment(sc, path):
    f0 = int(round(sc["start"] * FPS))
    f1 = int(round((sc["start"] + sc["dur"]) * FPS))
    cmd = [FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
           "-x264-params", "rc-lookahead=20:threads=2", path]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    arr = np.zeros((H, W, 4), np.uint8)
    surf = skia.Surface(arr)
    cv = surf.getCanvas()
    for f in range(f0, f1):
        cv.clear(skia.ColorBLACK)
        render(cv, f / FPS)
        cv.flush()
        pr.stdin.write(arr.tobytes())
    pr.stdin.close()
    pr.wait()


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "info":
        for sc in TL:
            print(f"{sc['id']:10s} start {sc['start']:7.2f} dur {sc['dur']:6.2f} cues {[round(c, 1) for c in sc['cues']]}")
        print("TOTAL", TOTAL)
    elif cmd == "still":
        sid = sys.argv[2]
        sc = [s for s in TL if s["id"] == sid][0]
        os.makedirs("stills", exist_ok=True)
        for spec in sys.argv[3:]:
            if spec.startswith("c"):
                i, off = spec[1:].split("+") if "+" in spec[1:] else (spec[1:], "0")
                lt = sc["cues"][int(i)] + float(off)
            else:
                lt = float(spec)
            still(sc["start"] + lt, f"stills/{sid}_{spec}.png")
    elif cmd == "seg":
        os.makedirs("seg", exist_ok=True)
        ids = sys.argv[2:] or [s["id"] for s in TL]
        for sc in TL:
            if sc["id"] in ids:
                render_segment(sc, f"seg/{sc['id']}.mp4")
                print("done", sc["id"], flush=True)
    elif cmd == "audio":
        build_audio()
    elif cmd == "final":
        with open("seg/list.txt", "w") as f:
            for sc in TL:
                f.write(f"file '{sc['id']}.mp4'\n")
        out = sys.argv[2]
        subprocess.run([FF, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "seg/list.txt", "-i", "audio/mix.wav",
                        "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                        "-shortest", "-movflags", "+faststart", out], check=True)
        print("written", out)
