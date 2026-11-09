#!/bin/sh
# Final render of every frame, headless, in ranges (one long Blender run slows down as it goes).
#   sh src/erva/blender/render_all.sh [first_range_start]
BL="C:/Program Files/Blender Foundation/Blender 5.1/blender.exe"
cd "$(dirname "$0")/../../.." || exit 1
START=${1:-1}
for r in "1 200" "201 400" "401 600" "601 800" "801 1000" "1001 1150" "1151 1296"; do
  set -- $r
  [ "$2" -lt "$START" ] && continue
  "$BL" -b blender/erva/erva.blend -P src/erva/blender/render_frames.py -- "$1" "$2" 2>&1 | grep -E "^frame|done|rror|Traceback"
done
echo "all ranges done"
