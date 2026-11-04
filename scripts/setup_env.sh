#!/usr/bin/env bash
# 一次性准备共享运行环境：~/.local/share/explainer-video/{venv,fonts,stub}
# 已存在的部分会跳过，可重复运行。
set -e
ENV=${EXPLAINER_ENV:-$HOME/.local/share/explainer-video}
SK="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ENV/fonts" "$ENV/stub"
cd "$ENV"
if [ ! -x venv/bin/python ]; then
  uv venv -q --python 3.12 venv
fi
uv pip install -q --python venv/bin/python skia-python edge-tts imageio-ffmpeg numpy
# 字体：中文 Noto Sans CJK SC（常规/粗体）+ 等宽 DejaVu Sans Mono（常规/粗体）
F=fonts
[ -s $F/NotoSansCJKsc-Regular.otf ] || curl -fsSL -o $F/NotoSansCJKsc-Regular.otf https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf
[ -s $F/NotoSansCJKsc-Bold.otf ]    || curl -fsSL -o $F/NotoSansCJKsc-Bold.otf    https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Bold.otf
if [ ! -s $F/DejaVuSansMono.ttf ] || [ ! -s $F/DejaVuSansMono-Bold.ttf ]; then
  curl -fsSL -o /tmp/dejavu.tar.bz2 https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.tar.bz2
  tar -xjf /tmp/dejavu.tar.bz2 -C /tmp && cp /tmp/dejavu-fonts-ttf-2.37/ttf/DejaVuSansMono.ttf /tmp/dejavu-fonts-ttf-2.37/ttf/DejaVuSansMono-Bold.ttf $F/
fi
# skia-python 在无 GPU / 无 libGL 的服务器上 import 会报 libEGL.so.1 缺失：编译一个空实现的桩库
if ! LD_LIBRARY_PATH=$ENV/stub venv/bin/python -c "import skia" 2>/dev/null; then
  if [ ! -s stub/libEGL.so.1 ]; then
    uv pip install -q --python venv/bin/python ziglang
    venv/bin/python -m ziglang cc -shared -fPIC -o stub/libEGL.so.1 "$SK/assets/gl_stub.c"
    cp stub/libEGL.so.1 stub/libGL.so.1
  fi
fi
LD_LIBRARY_PATH=$ENV/stub venv/bin/python -c "import skia, edge_tts, imageio_ffmpeg, numpy; print('env ok:', '$ENV')"
