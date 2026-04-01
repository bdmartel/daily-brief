# Daily Brief

Auto-generated daily audio briefing. Runs at 6 AM via macOS launchd. Deploys to GitHub Pages, opens in browser, plays intro audio.

## How It Works
1. **Input:** `~/.claude/daily-summaries/YYYY-MM-DD.md` (activity logs written by Claude Code chat logger)
2. **Generation:** `~/.claude/scripts/daily-dashboard.sh` reads yesterday's summary, sends to Claude API, builds HTML + TTS audio
3. **Output:** `index.html` + `audio/*.mp3` committed and pushed here
4. **Deploy:** GitHub Pages serves bdmartel.github.io/daily-brief/
5. **Alert:** Opens browser + plays intro audio through speakers at 6 AM

## File Locations
| What | Where |
|---|---|
| Deploy repo (this folder) | `~/projects/daily-brief/` |
| Generation script | `~/.claude/scripts/daily-dashboard.sh` |
| Schedule (launchd) | `~/Library/LaunchAgents/com.claude.daily-dashboard.plist` |
| Daily summaries (input) | `~/.claude/daily-summaries/` |
| Chat logs (input) | `~/.claude/chat-logs/` |
| Local dashboard | `~/.claude/daily-dashboard.html` |
| Logs | `/tmp/claude-daily-dashboard.log` and `.err` |

## Dependencies
- `claude` CLI (for summary generation via `claude -p`)
- `python3` + `edge_tts` (Microsoft Ava voice for TTS)
- `git` + SSH key (for GitHub push)
- ANTHROPIC_API_KEY (set in script header)

## Schedule
- **6:00 AM daily** via launchd (`com.claude.daily-dashboard`)
- Mac must be awake; if asleep, fires on next wake
- `--no-open` flag is NOT used in scheduled run (opens browser + plays audio)

## Manual Run
```bash
~/.claude/scripts/daily-dashboard.sh          # full run, opens browser
~/.claude/scripts/daily-dashboard.sh --no-open # generate only, no browser
```

## Debugging
```bash
cat /tmp/claude-daily-dashboard.log   # stdout
cat /tmp/claude-daily-dashboard.err   # stderr
launchctl list | grep daily-dashboard # check if agent is loaded (0 = OK)
```

## Archive
Previous briefs stored in `archive/YYYY-MM-DD.html` with audio in `archive/YYYY-MM-DD-audio/`.
