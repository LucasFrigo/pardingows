#!/bin/sh
# Renders every frame sequence one Blender at a time, retrying after a crash. Finished frames are kept and skipped, so a retry resumes.
# Don't run these side by side: several Blenders at once have run the GPU out of textures and crashed.
#   sh src/missao/blender/render_all.sh [step]     step 2 renders every second frame, for an animatic
BL="/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
STEP="${1:-1}"
for kind in story run end; do
  tries=0
  until "$BL" -b blender/missao/missao.blend -P src/missao/blender/render_frames.py -- "$kind" "$STEP" 2>&1 | grep -q "^done $kind"; do
    tries=$((tries + 1))
    echo "$kind crashed, retry $tries"
    if [ "$tries" -ge 8 ]; then
      echo "$kind failed after $tries retries"
      exit 1
    fi
  done
  echo "$kind done, $(ls "blender/missao/frames/$kind" | wc -l) frames"
done
