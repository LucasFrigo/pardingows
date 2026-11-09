# PARDINGOWS videos

TikTok videos for PARDINGOWS songs: one pipeline per video under `src/<video>/` (Node compositor, `timeline.json`,
sync tools) with Blender scenes in `src/<video>/blender/` and working files in `blender/<video>/`. The open Blender window
is driven through `node src/thps/bl.mjs` (the blender_mcp addon on 127.0.0.1:9876).

## 3D staging: measure, don't guess

Characters facing the wrong way, hands that miss what they hold, props off the mouth, characters floating in front of
chairs and characters clipping into each other kept coming back in review. These rules apply to every Blender video,
from the first animatic on:

- **Facing is computed, never typed.** Turn a character with a helper that takes the point it should face (and an
  optional bias towards the camera so the face reads), e.g. `face_rz(frm, to, bias, cam)` in `src/erva/blender/shots.py`.
  Our rigs face -Y at rz 0 and +X at rz +90: a hand-typed sign is wrong half the time. Blend towards the camera by
  ANGLE (blending direction vectors barely turns them), ~0.5 for two-shots: a Pardo in profile hides his face behind
  his own ear, so leads stand three-quarter, and walks cheat three-quarter too. Read the camera's position from the
  value just set (`location`), not `matrix_world`, which is stale until the next evaluation.
- **Hands reach, they aren't posed by eye.** Anything held (books, pipes, joints, a grabbed neck) puts the palm on a
  target point with the arm solver (`src/erva/blender/ik.py`, exact FK from the rest matrices), never with guessed
  shoulder and elbow angles.
- **Contact points are measured on the model.** Mouths come from a ray onto the face under the nose (`mouth()`), seats
  and backrests from the chair's own geometry (`set_lib.chair_measure`), feet from the shoe. Imported furniture comes in
  facing any way: aim it by its measured backrest (`aim_chair`), never assume an axis.
- **Spacing comes from real widths.** A Pardo is ~1 m ear to ear (huge head and ears): two-shots need ~1.3 m between a
  Pardo and the cobra, crowds go in staggered rows behind the leads, never between them. A 9:16 frame is narrow
  (width = 9/16 of the height): frame two-shots from the actors' measured span.
- **Props sit where the camera sees them.** Something in a mouth sticks out of the side facing the camera; nothing key
  sits in the bottom caption band (camera `shift_y` keeps characters high).
- **Objects built in code get names no imported model can have** (a prefix like `soul_jar`, `prop_`): Sketchfab models
  bring their own object names, and a clash silently renames ours to `.001`, so `OB["jar"]` moved the wrong object
  and the soul jar never appeared. Check that every prop the shots move resolves to the object you built.
- **Run the staging QA before any render**: `"$BLENDER" -b blender/<video>/<video>.blend -P src/<video>/blender/qa.py`.
  It builds sampled frames of every moment and reports clipping between actors (and with chairs) as surfaces crossing
  (normal-based inside tests lie on open imported models), hands or arms inside their own body, wrong facing, leads'
  faces turned too far from the camera, key subjects hidden or under the captions, and feet off the floor
  (`src/shared/blender_qa.py` holds the measurements; each video's `qa.py` declares per moment what must be visible,
  who faces whom and which contact is intended). Fix until it's clean, then look at a contact sheet, then render.
- **Before every final render, run the `staging-reviewer` subagent** (`.claude/agents/staging-reviewer.md`) without
  waiting to be asked: when all moments of a video are blocked and the animation is close to done, and again after any
  later change to staging, cameras or props. It runs the QA above (writing the video's `qa.py` if missing), renders and
  inspects a contact sheet, and reports wrong facing, overlapping meshes and contacts that don't connect. Fix
  everything it reports and re-run it until it returns CLEAN; only then render or hand the video to the user for
  review, and tell them what it caught and fixed.

## Working with the open Blender window

- Heavy rebuilds (sets, look, QA, renders) run headless on the saved .blend; the window is reloaded at milestones for
  the user to look at. Rebuilding scenes over and over inside the window (Rendered viewport recompiling every material)
  froze and crashed Blender. Keep the window's viewport in Solid while scripts run, and purge orphans after rebuilds.
- After a headless script saves the .blend, reload it in the window before running anything there: a window script
  that saves would otherwise overwrite the newer file with its stale copy.
