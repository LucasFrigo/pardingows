# PARDOS FELIZ: production brief

Approved design for a new TikTok video, written so a Claude Code session on another PC can run it with no access to the conversation that produced it. Nothing here has been built yet: only this file exists in `src/feliz/`.

**The video:** the smurf pardo struts around a cozy Animal Crossing-style island and shrugs off every bit of bad luck, then blasts a crew of debt-collecting lizard Bergs with Frutiger Aero.

**Output:** `out/pardos-feliz/pardos-feliz-tiktok.mp4`, 1080x1920, 30 fps, about 691 frames (23 s, exactly 12 bars).

**To start a session:** read this file, confirm the setup below, then begin at step 1. Stop for the user's OK after steps 1, 2, 3, 4 and 5. Commit only when asked.

## Setup on the new PC

**1. Get the files across.** On the original PC, these were not in git when this brief was written:

| Needed | State | What to do |
|---|---|---|
| `audio/PARDOS FELIZ.wav` | Untracked, 105.6 MiB | **Over GitHub's 100 MiB limit, so a plain push will be rejected.** Copy it by hand into `audio/` |
| `src/missao/`, `src/planeta/`, `src/shared/ps1.mjs` | Untracked | Commit and push, or copy. This video copies code from both folders |
| `src/feliz/PLAN.md` | Untracked | Commit and push, or copy |
| `blender/solucao/solucao.blend` and its textures | Tracked | Comes with git. It holds the rigged pardo |

`blender/missao/` and `blender/planeta/` aren't needed. Avoid `git add -A`: those folders are large.

**2. Install:**
- Node, then `npm install`.
- [uv](https://docs.astral.sh/uv/). `python` isn't assumed to be on PATH.
- Blender 5.1, with the `blender_mcp` addon enabled and connected, and a Sketchfab API key in the addon's preferences. Never print or save the key; `fetch_assets.py` reads it from the preferences.
- `faster-whisper-medium` and Demucs download on first use, roughly 2.5 GB together, all outside the repo.

**3. Check the Blender connection.** `node src/thps/bl.mjs cmd get_scene_info` should show the empty default scene, and `node src/thps/bl.mjs cmd get_sketchfab_status` should show a login. If this session exposes Blender MCP tools you can use them, but `bl.mjs` over `127.0.0.1:9876` is what earlier videos used.

**4. Paths.** 46 files under `src/` hardcode `C:\Users\lukeg\Projetos\pardingows`, and `src/missao/blender/render_all.sh` hardcodes the Blender 5.1 path.
- New scripts in `src/feliz/` must derive the repo root from their own location, and take the Blender path from a `BLENDER` environment variable.
- Copied code must have these paths replaced.
- `src/thps/` files reused unchanged are fine as long as they contain no such path; check them if the repo sits somewhere else on this PC.

**5. Hardware.** These limits came from the original laptop (Intel UHD 620, 16 GB), so re-test them instead of assuming them:
- One Blender at a time, because several ran that GPU out of textures.
- Decimating models over about 5,000 faces and capping textures at 512 px.
- The 10 s per frame render target.

The Wii-era 480x854 look was chosen on that laptop, and the choice was partly about render time. Keep it as the default, but make resolution a single setting and tell the user at step 4 what a sharper render would cost on this PC.

## Design decisions
All of these are the user's choices.

| Topic | Decision |
|---|---|
| Song window | 0:14.8–0:37.9: the 8 lines first supplied plus 4 more. The user first said 0:17–0:38, but the vocals don't start there (see Measured so far) |
| Story | "Nothing shakes him": bad luck hits, the pardo keeps smiling, villagers join in |
| Aero mix | Starts cozy, gloss builds through the song, all-out on `frutiger aero neles` |
| Look | Wii-era soft: rendered at 480x854, smoothly upscaled, with bloom. No PS1 filter |
| Captions | Animal Crossing-style dialog: cream rounded bubble, tilted name tag, dark brown rounded text, little bouncing arrow. No big words over the scene |
| Pardo | Glossy vinyl toy, shades and chain kept, new mouth that moves with the vocals |
| Berg | Debt-collector villain: a lizard villager in the Animal Crossing style, with a big nose, suit and tie |
| Villagers | Sketchfab animals; shades and a gold chain pop onto each one on `pardo repita` |
| Ending | Pure loop, no logo: hard cut on the beat back to `hoje` |
| Swear word | Caption reads `não f*do com tiktok`. The audio is unchanged |

**Brand limits (proposed, not yet confirmed by the user):** no Nintendo characters or logos, no Animal Crossing name on screen, no Windows or TikTok logos.

## Lyrics
The user's text, with spelling normalised for captions: `só` for `so`, `não` for `nao`, `FRUTIGER` for `fruitiger`. Tell the user about these so they can overrule them.

```
hoje eu sou um pardo feliz
tenho a pardo energia
nada vai abalar o pardo
comigo, pardo repita

hoje eu sou um pardo feliz
pardo só quer ser feliz
berg, o que o pardo quer?
o pardo quer ser feliz

beat plic ploc
não f*do com tiktok
frutiger aero neles
deixando os berg em choque
```

## Measured so far
**Tempo:** 125 BPM, so one beat is 0.48 s and one bar 1.92 s. This scored far above the alternatives (2.10, next best 1.08). Lines start on bars: 14.88 + 1.92n, ending at 37.92. The next sung line starts there, so the music has to cut there.

**Word times:** draft only, from `faster-whisper-medium` on the full mix, not isolated vocals. Two passes, with and without the lyrics as a prompt, agree on where lines start. Whisper misheard several words in the unprompted pass; the times below are mapped onto the real words.

| Line | Words and song seconds |
|---|---|
| 1 | hoje 14.84, eu 15.20, sou 15.38, um 15.58, pardo 15.84, feliz 15.94 |
| 2 | tenho 16.78, a 17.12, pardo 17.36, energia 17.78 |
| 3 | nada 18.68, vai 19.10, abalar 19.56, o 20.00, pardo 20.20 |
| 4 | comigo 20.54, pardo 21.18–21.34 (passes differ), repita 21.80 |
| 5 | hoje 22.56, eu 22.82, sou 23.06, um 23.22, pardo 23.38, feliz 23.74 |
| 6 | pardo 24.48, só 24.86, quer 25.16, ser 25.36, feliz 25.70 |
| 7 | berg 26.36, o 26.74, que 26.98, o 27.14, pardo 27.48, quer 27.78 |
| 8 | o 28.16–28.34 (passes differ), pardo 28.64, quer 28.98, ser 29.22, feliz 29.54 |
| 9 | **Unresolved.** Heard as `pesadinhos 30.00, pit 30.98, pit 31.22, plot 31.66` and as `pitch 29.98, pitch 31.28, plot 31.80`. Lyric is `beat plic ploc` |
| 10 | não 32.00, f*do 32.42, com 32.86, tik 33.16, tok 33.50 |
| 11 | frutiger 33.94, aero 35.06, neles 35.50 |
| 12 | deixando 35.94, os 36.74, berg 36.98, em 37.26, choque 37.52 |

The word before the window is `gozar`, about 14.12 to 14.8, and it must not leak in. The next line after the window begins about 37.84.

**Transcription call that worked**, run from the repo root:

```
PYTHONIOENCODING=utf-8 uvx --python 3.11 --from faster-whisper python -c "
from faster_whisper import WhisperModel
m = WhisperModel('medium', device='cpu', compute_type='int8')
segs, info = m.transcribe('audio/PARDOS FELIZ.wav', language='pt', word_timestamps=True,
    clip_timestamps='13,41', condition_on_previous_text=False, vad_filter=False, beam_size=5)
for s in segs:
    print(f'[{s.start:.2f}-{s.end:.2f}] {s.text}')
    print('   ' + ' '.join(f'{w.word.strip()}@{w.start:.2f}' for w in s.words))
"
```

## Storyboard
Times are line starts from the bar grid; step 1 replaces them with measured word times. `Aero` is the gloss level, 0 to 5.

| Song time | Name tag: caption | On screen | Aero |
|---|---|---|---|
| 14.88 | PARDO: hoje eu sou um pardo feliz | Morning. The door opens and the pardo struts out along the curved island, butterflies around | 0 |
| 16.80 | PARDO: tenho a pardo energia | Low tracking shot of the strut. A `PARDO ENERGIA` meter fills on `energia` | 0 |
| 18.72 | PARDO: nada vai abalar o pardo | Three fast cuts on the beat. `nada`: wasp nest drops on the pardo, face swollen, still smiling. `abalar`: falls in a pit, only hat and smile showing. `o pardo`: Berg hands over a giant letter, `VOCÊ DEVE 98.000`, and gets a thumbs up | 0 |
| 20.64 | PARDO: comigo, pardo repita | The pardo points at the camera. Villagers pop out of bushes, and shades and chains land on them on the beat | 1 |
| 22.56 | TODOS: hoje eu sou um pardo feliz | Town square: the whole pardo-fied crowd hops in unison | 2 |
| 24.48 | TODOS: pardo só quer ser feliz | Close-up on the pardo. First bubbles, the water starts to shine | 2 |
| 26.40 | PARDO: berg, o que o pardo quer? | Whip pan to Berg, huge nose in close-up, letter in hand | 2 |
| 28.32 | PARDO: o pardo quer ser feliz | The pardo tears the letter in half on `feliz`, paper confetti, Berg fumes | 3 |
| 30.24 | TODOS: beat plic ploc | A crew of Bergs arrives. Each word drops a giant glossy water droplet with a ripple | 4 |
| 32.16 | PARDO: não f*do com tiktok | A Berg holds out a shiny phone. The pardo kicks it into the sea, and a dolphin heads it back into the Berg's face | 4 |
| 34.08 | TODOS: frutiger aero neles | The pardo raises a glass orb and fires a wave of bubbles, aurora, droplets and flying koi. The island turns into a bright green hill under a deep blue sky | 5 |
| 36.00 | TODOS: deixando os berg em choque | Bergs jolt with electric arcs, ties standing straight up, noses glowing. The pardo dances in front. Hard cut | 5 |

The name tags are a guess at who sings each line and are one-word edits in the timeline. The debt letter, phone, dolphin and wave gags are proposals the user approved in outline, so adjust them if blocking shows they don't read.

## Lyric sync
**The user asked for extra attention here.** It gets its own step and sign-off before any animation exists. Claude can't hear audio, so measure what can be measured and rely on the user's ear for the final call.

1. **Isolate the vocals** with Demucs through `uv`, so the drums stop masking word starts. Keep the stem in `blender/feliz/sync/`. If Demucs fails, use the full mix and lean harder on point 4.
2. **Get word times** with `faster-whisper-medium` on the vocal track, using the lyrics above for spelling.
3. **Snap each word** to the nearest real vocal attack within 80 ms. List anything further out for a manual check rather than moving it silently. Line 9 is the least certain.
4. **Make a lyric proof video:** dialog bubble, beat marker and song over a plain sky, rendered in seconds. The user says which words feel late or early, and those numbers get changed in `src/feliz/timeline.json`.
5. **Drive everything from that one file.** Captions, cuts, gags and hops read `timeline.json`, and the mouth reads vocal loudness per frame from `src/feliz/vocal_env.json`. Captions are drawn in Node, so late sync fixes need no Blender re-render.
6. **Cut for a clean loop:** start just before `hoje` and after `gozar`, end just before `beat`, keeping exactly 12 bars so the beat stays steady across the loop.
7. **Check after encoding:** a script decodes the audio from the finished MP4, finds each word's attack and compares it to the frame the word appears on. AAC encoding can shift audio slightly, so this measures the real file. Target: every word within 1 frame.

Timeline format, following `src/missao/timeline.json`: times are song seconds, `v = song - start`, and frames are 1-based with `v = (f-1)/30`.

## Assets
All CC-BY or CC0 from the public Sketchfab API. **Chosen on name, face count and licence; nobody has seen them yet.** Step 2 builds a thumbnail sheet for approval (`src/missao/asset_sheet.mjs` is the template, and it also checks licences). URLs are `sketchfab.com/models/<uid>`. More can be found with `node src/thps/sketchfab_search.mjs "query"`.

| Need | Candidates |
|---|---|
| Trees | Animal Crossing Apple Tree `2ed2a55eebbb4b4fb60484390f611d20`, AC New Horizons Tree `b2321d4b5c084a9096e2e073bfe51618`, Prop Tree `886d00adb27f42b18a78004081a1f73c`, Cartoon tree `dde49eebec874267b52e53404655f9ca`, Coconut Tree `d141941578044b0f861ca83b36d4c411`, Palm Trees `55690379305145488e20afb05fc687e6` |
| Houses | Animal Crossing House `68fd7b3b59d8441e82e64960620ac0e2`, House `45a28a49e57e496e8b91d6de5c0ac88a`, Little Low Poly House `6198d1e97a2340bf92748fc4fdca0a71`, Cute lil house `745f09c22e8943b3bcc5fa47e0aea6ec`, Nook's Cranny `643a7dbe74694e4d838bb761a19d92ba` (Berg's bank, with a new sign) |
| Plants | Trees, flowers and grass `442904f26b87407d98871b50b49c4169`, Low poly nature pack `cb45d4926fcb4807bc93126b59325cf8`, Margarita flower `58ce34c65642408cb92eab784af2bd6c`, Bamboo Bush `d0d5eb345ff7420bb7f5c5239fcec637`, Water lily `04dd636204cd4b0db45a4fc82efa4385`, Lotus `12768caa111f446b8796e70f9cc53a23` |
| Town square | Fountain `d6d9e82784ae466c9b568e968f60d2e2`, Stylized Fence `9d8ce953d9414a07b974af8629dda93a`, Lamp Post `6f257cdc33e6470a836892cb7fa6a47f`, Wooden Bench `e53ad46c604c44e59a98bad27041cb19`, Picnic Table `fe35acda3a5245da8459d1a062e28190`, Mailbox `52cd14f6b8f54bb6bb26d728c02fd9e2`, Low Poly Apple `0176be079c2449e7aaebfb652910a854`, Low Poly Fruits v2 `7032a06ecb9b4370bdae87f656012356` |
| Berg's head | Cartoon Lizard `e45e5e07a86d4e159acf3007da95d614`, Aiden AC Form `53532e62af0c483e82ecfc5694f8c2a9`, Cartoon Alligator `8d067b5049c349c5af727b00e8f9dda6`, bobby `546e180a3f5e420a9d7c0969194f5a9d`, Anthropomorphic Lizard `2f3c7ea09f3944c6ac561389ceb52145`, Chibi Lizard `22697eb04fd746b39eced08ef957bc84`, Lizard Wizard `4a36fcde390f42b1957b79fd8c35146f` |
| Villagers | Toon Cat `b2bd1ee7858444bda366110a2d960386`, Lowpoly fox `01674a892f414c0681afdeb563cc8e13`, Stylized Duck `613776d688764d0aaa615d1c84379733`, Chibi Puppy `5be9012283c340de8d48a59bcfa0a39b`, Pots the Raccoon `2b3b6a5abe784dfe816fec5bf62542c2`, Little Girl `063f5f668fc14df0b095c0060b376882`, Roblox pet pack `0a2f57a889d54e44974d2fc58ece8477` |
| Gags | Beehive `ef6d00cb87684d60ae47a5c1d4e50f20`, Smiley Bee `76801d3aea024063bc5d91e4ee355508`, Envelope `196ab6a55cbd4b999beccbce3c7b92a0`, Clipboard `4a47897c83b94a988acfe271de27343d`, Mobile Phone `4ff99cf17b164e7b9790638c5d2ef4ce`, Boombox `d9f19a9ddce04dac8586b34869d0c1ba` |
| Aero | Frutiger Aero Friends `e303396edee34b64af752cc1cba8e0f7`, Frutiger Aero Character `23ad9c70727c4edeabbf7208b7c3511c`, Koi `236859b809984f52b70c94fd040b9c59`, Dolphin `f4abb460956240f98b7a6f19cc3037a1`, Low Poly Dolphin `3a7112396c7642df9201094a9b3634b0`, Clownfish `1bc61f9dc8e7483fab5b114f15231030`, Butterfly `0f24b085e8654e4db09c2fe681a79e3f`, Clouds `d9c1ff67f80841c6b1d8229dca5495a5`, Northern Lights `d66b8ca6f9b541beb54df5f115dce4fe`, Floating Island `b9a708aa70424f0699e9c4e3b5b5700a`, Hot Air Balloon `a420e9196b744919806ae532b3a11bf7`, Soap bubble `893be3cf512848ba842912b7c61566b1`, Drops `f8f24228aebf41f297c878ad82ea7db0` |

**Left out on purpose:** the Windows logo models, Mario and other Nintendo characters, and the many "New Horizons ROM/NSP" and "Download ... Free" listings, which are piracy spam.

**Built in code:** the curved island and water, the pit, bubbles, aurora ribbons, electric arcs, confetti, the torn letter, the glass orb, the suit and tie.

## Characters and world
- **Pardo:** append from `blender/solucao/solucao.blend` as `src/missao/blender/s01_setup.py` does, then restyle with smooth shading, one level of subdivision, soft texture filtering and glossy plastic.
- **Mouth:** a new dark piece on the head bone, covering the painted smile when open. Its size follows the vocal loudness while that character's name tag is up. The rig has no mouth or shape keys today.
- **Berg:** the rig's second copy (`P2`), for correct poses and chibi proportions, with lizard skin and a suit painted on. The hat and ears are replaced by a head from the model the user picks on the sheet, or one modelled in code if none works. Then a big nose and a tie.
- **Berg crew:** two or three extra copies of the rig.
- **Curved world:** the Animal Crossing rolling-log horizon. The ground is a big cylinder that rotates under the pardo, who walks in place at the top. Props sit at the arc distance matching their word's time, so each one reaches the pardo on that word, as with the runner in `src/missao/blender/path.py`.
- **Motion:** smooth 30 fps, not the 15 fps stepped poses of the PS1 videos. Crowd hops follow the beat grid.

**Rig gotchas already solved in the repo:**
- The rigged parts are rigid, each on one bone. Bone aliases are in `src/thps/blender/lib.py:8-14`.
- Rotate bones in armature rest axes with `set_bone_rot` (`lib.py:119-126`). The character faces -Y; +X bends forward.
- Scale is `SCALE = 0.23`. Leg IK constraints named `foot` must have influence 0 for free poses, and each pose must then carry its own legs (`s01_setup.py:50-54`).
- One object holds one pose per frame, so two characters on screen need two rigs.
- Setting `.parent` clears `matrix_parent_inverse`; `P2_body` is the hip empty and `P2_torso` the mesh (`src/thps/blender/s03_rig.py:104-107`).
- Attach new pieces with the armature in rest pose (`src/planeta/blender/build.py`).
- Check the rear view: `blender/solucao/review/01-personagem.png` shows white parts nearly vanishing there.

## Pipeline
**Rendering:** Blender EEVEE at 480x854, 30 fps, PNGs to `blender/feliz/frames/`. Step 4 times a real frame. If it's too slow, lower samples and shadow quality first.

**Compositing (Node):** read each PNG, upscale to 1080x1920, add bloom and lens flare scaled by the Aero level, draw the dialog UI on top, then pipe to ffmpeg with the same encode settings as `src/missao/render.mjs`.

**New dependency:** `@napi-rs/canvas`, because `src/shared/font.mjs` is a capitals-only bitmap font and can't produce this look.

**Font:** a free rounded font close to the game's, likely Fredoka or Nunito. Check it has `ã ç õ ó ê`, then store it with its licence in `src/feliz/fonts/`.

**New in `src/feliz/`:**
- `timeline.json`, `vocal_env.json`
- `ui.mjs`: dialog bubble, name tag, meter, as a pure function of video time
- `video.mjs`, `stills.mjs`, `asset_sheet.mjs`
- `render.mjs`, including a `--proof` mode for the lyric proof
- `sync/`: word timing, attack detection and the check on the finished MP4

**New in `src/feliz/blender/`:**
- `fetch_assets.py`, `s01_setup.py` to `s08_shots.py`, following `src/missao/blender/`
- `set_lib.py`: copied from Missão, with glossy smooth materials replacing `ps1_material`
- `poses_feliz.py`, `path.py`, `build_all.py`, `render_frames.py`, `render_all.sh`, review-sheet scripts

**Reused unchanged:** `src/thps/bl.mjs`, `src/thps/blender/lib.py`, `src/thps/blender/poses.py`, `src/planeta/blender/build.py`, `src/thps/sketchfab_search.mjs`.

**Adapted by copying:** the `K`, `smurf` and `put_cam` helpers from `src/missao/blender/s08_shots.py`, without its pass that forces every key to stepped.

**Not used:** `ps1Colour`, `src/shared/font.mjs`.

**Small edits to existing files:**
- `.gitignore`: add `blender/feliz/frames/`, `blender/feliz/assets/*/`, `blender/feliz/sync/`.
- `package.json`: add `feliz:stills`, `feliz:render` and the canvas dependency.

**Blender file:** the first script saves the empty scene as `blender/feliz/feliz.blend`, and refuses to run on any other open file. `solucao.blend` is only ever read. Run long builds and renders headless (`blender -b`), with retry and resume as in `src/missao/blender/render_all.sh`.

## Steps
Each stage leaves a sheet in `blender/feliz/review/`. **Stop for the user's OK after steps 1 to 5.**

1. **Sync:** isolate vocals, word times, write the timeline, lyric proof MP4.
2. **Assets:** thumbnail sheet, user's picks (including Berg's head), download, `blender/feliz/assets/CREDITS.txt`.
3. **Cast:** glossy pardo with mouth, Berg, pardo-fied villagers, turnaround sheet.
4. **World and look:** curved island plus two stills, cozy and full Aero, and the per-frame render time.
5. **Blocking:** key everything, low-quality animatic with captions against the song.
6. **Gags and Aero:** wasps, pit, letter, phone and dolphin, droplets, orb wave, aurora, electric arcs.
7. **Final:** full render, composite, sync check on the MP4.

**Likely weak spots:**
- Smoothing the rigid body parts may open visible gaps at the joints. Check this first on the cast sheet.
- A lizard head on the smurf body may look odd. Modelling one in code is the fallback.
- Three gags in 1.9 s may be too fast to read. If so, drop to two and move the pit or the wasps.
- Unrigged villagers will only hop and bob.

## Verification
- `ffmpeg -i` on the MP4 (`ffprobe` isn't bundled with `ffmpeg-static`): 1080x1920, 30 fps, expected frame count, AAC audio.
- Per-word sync table from the finished file, every word within 1 frame. The user then listens to it.
- Loop check: last frame into first frame on the beat, no `gozar` or `beat` leaking at either end.
- Accents, `f*do` and name tags readable at phone size, and the bubble clear of TikTok's own interface.
- Contact sheet across the whole song showing the gloss really builds from cozy to full Aero.
- `git status` shows `solucao.blend` and other videos' files unchanged.
- `CREDITS.txt` covers every model that actually appears.

## Raise with the user before publishing
1. **Rights.** CC-BY credits go in the description, and the smurf model's licence is still unverified, as noted in earlier videos' `CREDITS.txt`. A few candidates are fan models of Nintendo designs, such as the tree, house and shop, and are on the sheet so the user can veto them. Copying the game's style should be safer than using its characters or logos, but a complaint can't be ruled out.
2. **Reach.** The caption is censored, but the sung line is still explicit and names TikTok, on TikTok.
