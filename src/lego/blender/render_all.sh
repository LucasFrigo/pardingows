#!/bin/sh
# Renders every planned frame with one Blender, retrying after a crash. Finished frames are kept and skipped, so a retry resumes.
#   BLENDER="/path/to/blender.exe" sh src/lego/blender/render_all.sh [engine] [res] [samples] [dir]
#   animatic: sh src/lego/blender/render_all.sh CYCLES 0.5 12 blender/lego/frames_animatic
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
BL="${BLENDER:-blender}"
ENGINE="${1:-CYCLES}"
RES="${2:-1.0}"
SAMPLES="${3:-}"
DIR="${4:-$ROOT/blender/lego/frames}"
tries=0
until "$BL" -b "$ROOT/blender/lego/lego.blend" -P "$HERE/render_frames.py" -- "$ENGINE" "$RES" "$SAMPLES" "$DIR" < /dev/null 2>&1 | grep --line-buffered -E "^(progress|done|engine)" | tee /dev/stderr | grep -q "^done "; do
  tries=$((tries + 1))
  echo "render stopped, retry $tries"
  if [ "$tries" -ge 8 ]; then
    echo "failed after $tries retries"
    exit 1
  fi
done
echo "all done, $(ls "$DIR" | wc -l) frames in $DIR"
