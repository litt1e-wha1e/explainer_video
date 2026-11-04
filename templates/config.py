# 每个视频项目一份的配置
TAG = "科普讲解"              # 右上角常驻标签
VOICE = "zh-CN-YunxiNeural"   # edge-tts 音色（男声，科普感强）；女声可用 zh-CN-XiaoxiaoNeural
RATE = "+6%"                  # 语速
LEAD_FIRST = 1.2              # 第一个场景开口前的留白（秒），其余场景 0.7

# 本项目额外的读音修正（优先于 say.py 内置表，长的写在前面）
# 英文术语：拆成 TTS 好读的形式，例如 ("LayerNorm", "Layer Norm")
EXTRA_EN = [
]
# 多音字：替换成读音唯一的同音字，只影响朗读，不影响字幕，例如 ("调参", "条参")
EXTRA_POLY = [
]
