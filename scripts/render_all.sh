#!/usr/bin/env bash
# 用法（在项目目录里）: bash render_all.sh "<输出路径.mp4>"
# 两个进程并行渲染各场景（按时长均分）→ 混音 → 拼接并统一响度。
# 适合放后台跑：完成打印 ALLDONE，任何一步失败打印 FAIL 并退出非零。
set -o pipefail
OUT=${1:?usage: render_all.sh out.mp4}
export LD_LIBRARY_PATH=$PWD/stub
PY=venv/bin/python
read -r GA GB < <($PY - <<'PYEOF' 2>/dev/null
from make import TL
a, b, sa, sb = [], [], 0, 0
for x in sorted(TL, key=lambda x: -x["dur"]):
    if sa <= sb: a.append(x["id"]); sa += x["dur"]
    else: b.append(x["id"]); sb += x["dur"]
print(",".join(a), ",".join(b))
PYEOF
)
mkdir -p seg
$PY make.py seg ${GA//,/ } > ra.log 2>&1 & PA=$!
$PY make.py seg ${GB//,/ } > rb.log 2>&1 & PB=$!
wait $PA; EA=$?; wait $PB; EB=$?
N=$(cat ra.log rb.log | grep -c "^done")
TOTAL=$($PY -c "from make import TL; print(len(TL))" 2>/dev/null)
if [ $EA -ne 0 ] || [ $EB -ne 0 ] || [ "$N" != "$TOTAL" ]; then
  echo "FAIL render ($N/$TOTAL)"; grep -v Fontconfig ra.log rb.log | tail -20; exit 1
fi
echo "RENDERED $N/$TOTAL"
# 混音必须在渲染结束后单独跑：1GB 内存的机器上与渲染并行会 OOM
$PY make.py audio 2>&1 | grep -v Fontconfig || { echo "FAIL audio"; exit 1; }
$PY make.py final "$OUT" 2>&1 | grep -v Fontconfig || { echo "FAIL final"; exit 1; }
echo "ALLDONE $OUT"
