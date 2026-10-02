# Session State
**Updated:** 2026-10-02 10:38
**Chat:** daily-brief-real-recordings

## Currently Working On
Done: the wake-up bed is a real field recording each morning (Ben, 2026-10-02: synthesized sounds "artificial", the brook "was competing with the voice"). First live morning: Oct 3 (Echo mode build 5:40, Echo plays at 6:00). Waiting on Ben's ear: sample sent (today's lesson + poem over Bailey Island rain).

## Done This Session
- Root cause of "competing": the synthesized brook had 46% energy at 1-4 kHz + 78% envelope flutter at 3-12 Hz (syllable rate); the garden Ben liked had 0% at 1-4 kHz.
- tools/fieldbed.py (pick/render/fetch/list) + tools/fieldbeds.json (26 CC0/CC BY Freesound recordings, chosen from ~1,600 results by measured spikes/rumble/clipping/speech-band energy). Cache assets/field/ (gitignored, ~300 MB, filled).
- Render: seeded random stretch, high-pass, events >8 dB softened 3:1, -29 LUFS, clicks under -12 dBFS, voice pocket (1-4 kHz -6 dB under the voice, level unchanged), 45 s in / 20 s out.
- daily-dashboard.sh: pick + build_bed use fieldbed.py; caption links + credits the recording; 14-morning history; knob ~/.claude/daily-brief-bed-pocket "carve duck" (default "6 0"). soundscape.py retired (kept).
- Verified: all 26 render (3-11 s each), bare-launchd environment (python3 3.9 + numpy/scipy/soundfile), UTF-8 captions, season/avoid/fallback logic, Range download path, end-to-end pick -> bed -> Echo mix with the script's own code.

## Next Steps
- Oct 3 morning: check audio/bed.txt, the poem-card caption, and /tmp/fieldbed.err (should be empty).
- Ben's verdict on the sample/first mornings: drop any recording he dislikes (delete its fieldbeds.json entry); if the bed still competes, raise the carve (ask before any duck).

## Key Decisions / Context
- CC0 / CC BY only: the mix is public on GitHub Pages; CC BY needs the credit shown under the poem.
- No level duck by default: Ben rejected an 8 dB duck in Aug 2026; the pocket is spectral only.
- Freesound CDN ~78 KB/s per connection: never download at 5:40; picks use cached files only.
- Whisper can't screen nature audio for voices (hallucinates); screened by recordist descriptions.
