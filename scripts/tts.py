import asyncio, json, os, subprocess, re
import edge_tts, imageio_ffmpeg
from script import SCRIPT
from say import say

import config
VOICE = getattr(config, "VOICE", "zh-CN-YunxiNeural")
RATE = getattr(config, "RATE", "+6%")
FF = imageio_ffmpeg.get_ffmpeg_exe()
os.makedirs("audio", exist_ok=True)


def dur(path):
    out = subprocess.run([FF, "-i", path], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


async def one(sem, text, path):
    async with sem:
        for attempt in range(5):
            try:
                if not os.path.exists(path) or os.path.getsize(path) < 1000:
                    await edge_tts.Communicate(text, VOICE, rate=RATE).save(path)
                return
            except Exception as e:
                print("retry", path, e)
                await asyncio.sleep(2)
        raise RuntimeError(path)


async def main():
    sem = asyncio.Semaphore(4)
    jobs, meta = [], []
    for sid, label, sents in SCRIPT:
        for i, s in enumerate(sents):
            sub, sp = (s, s) if isinstance(s, str) else s
            p = f"audio/{sid}_{i:02d}.mp3"
            jobs.append(one(sem, say(sp), p))
            meta.append(dict(scene=sid, i=i, sub=sub, say=say(sp), path=p))
    await asyncio.gather(*jobs)
    for m in meta:
        m["dur"] = dur(m["path"])
    json.dump(meta, open("audio/meta.json", "w"), ensure_ascii=False, indent=1)
    print("total speech", sum(m["dur"] for m in meta))


asyncio.run(main())
