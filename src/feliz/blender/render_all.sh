#!/bin/sh
# Renders every frame with one Blender, retrying after a crash. Finished frames are kept and skipped, so a retry resumes.
#   BLENDER="/path/to/blender.exe" sh src/feliz/blender/render_all.sh [step]     step 2 renders every second frame, for an animatic
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
BL="${BLENDER:-blender}"
STEP="${1:-1}"
tries=0
until "$BL" -b "$ROOT/blender/feliz/feliz.blend" -P "$HERE/render_frames.py" -- "$STEP" < /dev/null 2>&1 | tee /dev/stderr | grep -q "^done "; do
  tries=$((tries + 1))
  echo "render stopped, retry $tries"
  if [ "$tries" -ge 8 ]; then
    echo "failed after $tries retries"
    exit 1
  fi
done
echo "all done, $(ls "$ROOT/blender/feliz/frames" | wc -l) frames"
