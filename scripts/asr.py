import json, sys, subprocess, numpy as np, imageio_ffmpeg
FF=imageio_ffmpeg.get_ffmpeg_exe()
def load(p):
    raw=subprocess.run([FF,'-v','quiet','-i',p,'-f','s16le','-ac','1','-ar','16000','-'],capture_output=True).stdout
    return np.frombuffer(raw,np.int16).astype(np.float32)/32768
from faster_whisper import WhisperModel
name = sys.argv[1] if len(sys.argv) > 1 else "small"
m = WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=2)
meta = json.load(open("audio/meta.json"))
out = []
for x in meta:
    segs, _ = m.transcribe(load(x["path"]), language="zh", beam_size=3, initial_prompt="以下是普通话的句子，包含英文术语。")
    txt = "".join(s.text for s in segs)
    out.append(dict(path=x["path"], sub=x["sub"], asr=txt))
    print(x["path"], "|", x["sub"], "\n   ->", txt, flush=True)
json.dump(out, open(f"audio/asr_{name}.json", "w"), ensure_ascii=False, indent=1)
