#!/bin/sh
# Renders a frame sequence with one Blender, retrying after a crash. Finished frames are kept and skipped, so a retry resumes.
#   BLENDER="/path/to/blender.exe" sh src/zombies/blender/render_all.sh [main|judge|mug] [step]
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
BL="${BLENDER:-blender}"
KIND="${1:-main}"
STEP="${2:-1}"
LOG="$ROOT/blender/zombies/frames/render_$KIND.log"
mkdir -p "$ROOT/blender/zombies/frames"
tries=0
until "$BL" -b "$ROOT/blender/zombies/zombies.blend" -P "$HERE/render_frames.py" -- "$KIND" "$STEP" < /dev/null > "$LOG" 2>&1 && grep -q "^done " "$LOG"; do
  tries=$((tries + 1))
  echo "render stopped, retry $tries"
  if [ "$tries" -ge 8 ]; then
    echo "failed after $tries retries"
    exit 1
  fi
done
grep "^done " "$LOG"
echo "$KIND: $(ls "$ROOT/blender/zombies/frames/$KIND" | wc -l) frames on disk"
