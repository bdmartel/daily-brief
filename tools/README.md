# Tools

## ethgarden-render.mjs — garden ambience renderer

Offline re-render of the generative ambient audio from Jackson's
https://eth-garden.vercel.app/ (synthesis code ported from the site's JS
bundle, with his permission). The site synthesizes everything live with the
Web Audio API — there is no audio file to download — so this script rebuilds
the identical signal chain in an `OfflineAudioContext`:

- Drone: A2 + E3, sine + triangle (+7 cents, slow LFO wobble), lowpass 480 Hz
- Pads: A-major pentatonic (two pools), paired ±5-cent sines, LP 1100 Hz, 2.6s swell, every 5–10s
- Chimes: high pentatonic, sine + 2.01× partial pluck, every 9–21s at 75%
- Bus: convolver reverb (3.2s decaying-noise impulse, wet 0.9 / dry 0.7), master 0.14, LP 2200 Hz

Deterministic: same seed → same take (mulberry32 PRNG replaces Math.random).

### Re-render `audio/garden-ambience.mp3`

```bash
npm install node-web-audio-api        # one-time, anywhere
node tools/ethgarden-render.mjs 390 20260818 /tmp/ethgarden-390s.wav

# Wake-up envelope: +5dB trim (≈ −29 LUFS throughout), 45s fade-in,
# fade-out 6:10–6:30. No duck: the voice (≈ −21 LUFS) rides ~8 dB above
# the bed, which Ben tuned by ear on 2026-08-18 (an −8 dB duck buried it).
ffmpeg -y -i /tmp/ethgarden-390s.wav -af "volume=5dB,afade=t=in:st=0:d=45:curve=tri,afade=t=out:st=370:d=20" -c:a libmp3lame -b:a 128k -ar 44100 assets/garden-ambience.mp3
```

Output goes to `assets/` (NOT `audio/`): the daily rebuild `rm -rf`'s `audio/`
and deleted the first copy (2026-08-18).

Change the seed for a different "performance" of the same garden. The voice
enters after the `sleep 180` in the alarm block of
`~/.claude/scripts/daily-dashboard.sh`; the file just holds its level there.

## soundscape.py — RETIRED 2026-10-02 (synthesized scenes; replaced by fieldbed.py, kept for reference)

`python3 tools/soundscape.py --list` prints the 14 scenes. `--pick [--avoid a,b]` chooses one and
prints `scene|description|seed`; `--scene NAME|random --seconds S --out bed.wav [--seed N]`
renders it (44.1 kHz stereo WAV, RMS −20 dBFS, soft-clipped). Every render is randomized (scale,
root note, rates, densities, panning), so the same scene never repeats exactly. The `garden` scene
calls `ethgarden-render.mjs` with a fresh seed and needs `node-web-audio-api` resolvable from `tools/`
(a one-time `npm install node-web-audio-api` anywhere under your home works; on the Mac mini it lives in
`~/node_modules`). Needs python3 with numpy, scipy, soundfile (all present on
the Mac mini). `daily-dashboard.sh` applies loudness (−29 LUFS) and the fade envelope with ffmpeg.

## fieldbed.py — the wake-up bed from real field recordings (2026-10-02)

Ben found the synthesized scenes artificial and said the brook "was competing with the voice", so the
bed is now a real recording each morning. `fieldbeds.json` is the catalog: 26 CC0 / CC BY recordings
(mostly Freesound HQ previews) with caption, recordist, license, source page, `end` (seconds used),
high-pass and optional `months`. The audio is cached in `assets/field/` (gitignored).

```bash
python3 tools/fieldbed.py --list                    # catalog + cached seconds + seasons
python3 tools/fieldbed.py --fetch                   # download anything missing (slow CDN: ~80 KB/s per connection)
python3 tools/fieldbed.py --pick --avoid a,b        # -> id|caption|seed|credit|source (cached recordings only)
python3 tools/fieldbed.py --render hallsands --seconds 90 --voice 40:80 --out /tmp/x.wav
```

A render takes a seeded random stretch of the recording (loops with an 8 s crossfade if short),
high-passes it, softens events more than 8 dB over the body (3:1), sets -29 LUFS, holds clicks under
-12 dBFS, carves 6 dB out of 1-4 kHz while the voice plays (`--carve`, `--duck` 0 by default), and
fades 45 s in / 20 s out. `daily-dashboard.sh` limits and encodes it to `audio/wakeup-bed.mp3`.
To add a recording: append an entry (CC0 or CC BY only, the page shows the credit) and run `--fetch`.

## recent_mornings.py — the "Last five mornings" card (2026-10-15)

Lists this morning plus the four before it on the brief page (6 AM Echo mix, lesson, poem, sound),
from `audio/` and the newest `archive/*-audio/` folders. Archive folders are named for the day after
their audio played, so each folder's morning comes from its archived page title + 1 day.
`daily-dashboard.sh` runs it right before the commit; `--print` previews the card:

```bash
python3 tools/recent_mornings.py --today 2026-10-15 --print
```

Each row also gets **▶ poem · lesson · poem** when the folder has `poem-first.mp3`, `poem-preface.mp3`
and `poem-again.mp3` (Ben: "POEM, LESSON, POEM as a way to digest it").

## poem_split.py — the poem's two readings, apart (2026-10-15)

`poem.mp3` is one take read twice (reading, 1.5 s of silence, the same reading, "So — up!"). This
cuts it into `poem-first.mp3` (the first reading alone) and `poem-again.mp3` (the second reading and
the closer) for the button above. The morning script writes those itself, so this is for older
mornings: it finds the lag where the file matches itself (0.90–0.98 on all 32 doubled mornings, under
0.07 on single readings) and checks that the pause between is digital silence.

```bash
python3 tools/poem_split.py archive/2026-10-14-audio --check   # report only
python3 tools/poem_split.py archive/2026-10-14-audio           # write the two files
```

