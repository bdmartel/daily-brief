# Session State
**Updated:** 2026-10-15 23:05
**Chat:** daily-brief-real-recordings

## Currently Working On
Weekly poetry workshop (poetry.benmartel.com): generator, deploy, guard hook and anthology are done; next is building the first week (Oct 9-15) with `python3 tools/poem_roundup.py --end 2026-10-15`, checking it, and committing. Then ask Ben about storage for the sounds.

## Done This Session
- Oct 2: real field recordings as the wake-up bed. Oct 15: Last 5 mornings card, poem · lesson · poem button.
- Oct 15: tools/poem_roundup.py, poetry/deploy.sh, tools/anthology.json (60 poems, verified), guard hook (--if-due after the brief), lesson.json written by the script, verse cleanup for doubled endings, directory chip.

## Next Steps
- Must save the first week before 5:40 AM Oct 16, or the guard's --if-due will build Oct 4-10 at 5:45 (today is blocked by ~/.claude/poem-roundup-state = fail 3).
- Commit daily-brief (tools, poetry/, CLAUDE.md, lesson.json files, split mp3s, index.html card link).
- Ask Ben: DO volume (~$2.50/mo for 25 GB) so the brief's sounds can move to poetry.benmartel.com/m/ (droplet 87% full; doctl token dead).

## Key Decisions / Context
- Sundays, Sun-Sat week, no overlap with a saved week; first week built by hand, next Oct 25.
- Examples quote real poets only from anthology.json by id + line numbers; anything unverifiable is dropped.
- Backups: scratchpad daily-dashboard.sh.before-roundup, daily-dashboard-guard.sh.before-roundup.
