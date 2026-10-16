# Session State
**Updated:** 2026-10-15 21:21
**Chat:** daily-brief-real-recordings

## Currently Working On
Done (Oct 15 evening): each morning on the Last 5 mornings card has "▶ poem · lesson · poem" (Ben: "POEM, LESSON, POEM as a way to digest it"). Live on today's page; the morning script makes the pieces daily from Oct 16.

## Done This Session
- Oct 2: wake-up bed = a real field recording each morning (tools/fieldbed.py + fieldbeds.json, 26 CC0/CC BY); speech band carved under the voice.
- Oct 15: tools/recent_mornings.py fills a "Last 5 mornings" card (6 AM Echo mix, lesson, poem, sound per day) before each commit.
- Oct 15: poem · lesson · poem button: poem-first.mp3 (one reading) → poem-preface.mp3 → poem-again.mp3 (one reading + "So — up!"). daily-dashboard.sh saves both from its takes; tools/poem_split.py cut Oct 11-15 from poem.mp3 (whisper-checked). Card now sits between <!--last-five-mornings--> comments so a re-run replaces it in place.

## Next Steps
- Oct 16 morning: confirm the card shows Oct 16 + Oct 12-15, every row has the poem · lesson · poem button, and audio/poem-first.mp3 + poem-again.mp3 exist; /tmp/recent_mornings.err empty.

## Key Decisions / Context
- poem.mp3 = one take read twice + closer, so the button uses single readings; the closer stays once, at the end.
- Script backups: scratchpad daily-dashboard.sh.before-digest (and .before-last5, .orig).
- Archive folders are named for the day after the audio played (launchd's grep lacks -P); don't fix without migrating.
