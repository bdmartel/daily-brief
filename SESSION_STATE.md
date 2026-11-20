# Session State
**Updated:** 2026-11-20 12:50
**Chat:** daily-brief-all-poems

## Currently Working On
Workshopping the morning poem so it stops feeling like Groundhog Day. The doors and currents checklist is live (Ben ticked all 42 doors and 23 currents) with 20 poems of memory, starting with the Nov 21 5:00 build. Three sample poems sit in a card on the Nov 20 brief; the third plays as a full morning (lesson, then the poem twice, no nature sound). Ben wants a sample poem in chat with each reply while this is tuned.

## Done This Session
- Nov 8: "All the poems" accordion on the brief page; "So — up!" closer removed from future poems.
- Nov 17: poem card play-all, lessons tab; workshop and brief players got pause, repeat, whole-poem toggle; workshop dark mode.
- Nov 14: nature recording turned off with the console's garden switch (flip it back on to restore).
- Nov 20: "How this poem was made" note added under the poem for Nov 21 to 27.
- Nov 20: poem doors page at lists.benmartel.com/poem (42 doors, 23 currents), wired into the morning build with 20-poem memory.

## Next Steps
### For Ben

- **Fix the Echo wake-up routine.** In the Alexa app, the "Morning Bluetooth Connect" routine's "open sunrise verse" step never reaches the skill (failed Nov 17 and 18). Replace it with the News action (your Daily Brief flash briefing), then press play on the routine to test.
### Waiting on someone else
- Nothing.
### For Claude
- **Check the Nov 21 poem used the new doors and currents.** Read the run log for the "Poem pick:" line and /tmp/poem_currents.err, and confirm a Nov 21 row landed in ~/.claude/daily-brief-poem-history.jsonl, and that the Nov 21 page shows the "How this poem was made" note under the poem (it runs Nov 21 to 27, then stops by itself).

## Key Decisions / Context
- Poem doors and currents: see CLAUDE.md "Poem Doors and Currents". Ben excluded "where the sound recording came from" as a current.
- Older sound folders are at a/<folder name>; new mornings at m/<date> on Cloudflare.
- Ben, Nov 15, 2026: keep all audio. Never purge or delete recordings, including the old copies in the GitHub history. If space ever runs short, tell him instead of deleting.
- Backups in the scratchpad: daily-dashboard.sh.bak-poemdoors (before the Nov 20 poem change).

## Notes from Ben (ops board)
- (Nov 15) on "Optional: purge old audio from GitHub history": "I want to keep all audio. If more space is needed lmk, what?" Handled Nov 15, 2026: step removed and the keep-all-audio rule recorded above.
