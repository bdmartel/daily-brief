# Session State
**Updated:** 2026-10-16 00:20
**Chat:** daily-brief-real-recordings

## Currently Working On
Waiting on Ben's decision about storage for the brief's sounds (droplet 87% full, 1.2 GB free; audio 1.3 GB, +15 MB a day). Everything else from Oct 15 is done and live.

## Done This Session
- Oct 2: real field recordings as the wake-up bed. Oct 15: Last 5 mornings card; poem · lesson · poem button.
- Oct 15-16: weekly poetry workshop live at poetry.benmartel.com (first week Oct 9-15; tools/poem_roundup.py, tools/anthology.json, poetry/deploy.sh, guard --if-due on Sundays from Oct 25), directory chip, lesson.json from the script, doubled-ending verse cleanup.

## Next Steps
- If Ben approves a DO volume: create it (doctl needs a fresh token: `doctl auth init`), mount it on the droplet, serve audio at poetry.benmartel.com/m/<morning date>/, point the brief, card, feed and workshop there, then stop committing audio to GitHub.
- Oct 16 morning: confirm audio/lesson.json exists, the poem has one So - up, and the card shows Oct 12-16.

## Key Decisions / Context
- Workshop audio uses GitHub URLs for now. Today's part falls back from archive/<tomorrow>-audio/ to audio/.
- claude-opus-5-5 thinking counts toward max_tokens (48k now).
- Backups in the scratchpad: daily-dashboard.sh.before-roundup, daily-dashboard-guard.sh.before-roundup.
