#!/usr/bin/env bash
# 用法: new_project.sh <项目目录> "<右上角标签，如 minbpe · BPE 分词器>"
# 复制引擎脚本和模板，软链共享环境（venv / fonts / stub）。
set -e
DIR=$1; TAG=${2:-"科普讲解"}
[ -n "$DIR" ] || { echo "usage: new_project.sh <dir> <tag>"; exit 1; }
ENV=${EXPLAINER_ENV:-$HOME/.local/share/explainer-video}
SK="$(cd "$(dirname "$0")/.." && pwd)"
[ -x "$ENV/venv/bin/python" ] || bash "$SK/scripts/setup_env.sh"
mkdir -p "$DIR"; cd "$DIR"
for f in eng.py common.py make.py tts.py say.py check.py sheets.py asr.py render_all.sh; do [ -e "$f" ] || cp "$SK/scripts/$f" .; done
for f in config.py script.py scenes.py scenes_a.py; do [ -e "$f" ] || cp "$SK/templates/$f" .; done
sed -i "s|^TAG = .*|TAG = \"$TAG\"|" config.py
ln -sfn "$ENV/venv" venv; ln -sfn "$ENV/fonts" fonts; ln -sfn "$ENV/stub" stub
mkdir -p audio seg sheets
echo "project ready: $(pwd)"
