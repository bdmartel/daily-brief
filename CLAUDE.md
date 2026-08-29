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
| Guard/dispatcher (what launchd runs) | `~/.claude/scripts/daily-dashboard-guard.sh` |
| Schedule (launchd) | `~/Library/LaunchAgents/com.claude.daily-dashboard.plist` |
| Once-per-day state | `~/.claude/daily-brief-lastrun` (`YYYY-MM-DD done` or `fail N`) |
| Daily summaries (input) | `~/.claude/daily-summaries/` |
| Chat logs (input) | `~/.claude/chat-logs/` |
| Local dashboard | `~/.claude/daily-dashboard.html` |
| Run log | `~/.claude/logs/daily-dashboard.log` (guard's own stdout/err: `daily-dashboard-guard.log`/`.err` in same dir) |

## Dependencies
- `claude` CLI (for summary generation via `claude -p`)
- `SwitchAudioSource` (brew switchaudio-osx) — alarm routes audio to the bedroom Bluetooth speaker "B06 Pro" (fallback: Mac mini Speakers); `blueutil` optionally reconnects it if granted Bluetooth privacy permission
- `python3` + `edge_tts` (Microsoft Ava voice for TTS)
- `git` + SSH key (for GitHub push)
- ANTHROPIC_API_KEY (set in script header)

## Schedule
- launchd (`com.claude.daily-dashboard`) runs the **guard** every 2 minutes (`StartInterval 120`); the guard fires the real script once per day at the first tick at/after **6:00 AM**
- Fired 6:00–6:59 → full run (wake-up alarm allowed; wakeup-state toggle still governs). Fired 7:00+ (Mac was asleep/off at 6) → catch-up run with `--no-open` (silent)
- Success = today's commit exists AND is pushed (guard checks git, not exit codes). On failure it retries on later ticks, max 3 attempts/day
- **Echo mode** (`~/.claude/daily-brief-echo-mode` contains `on`): start shifts **20 min earlier** (default 5:40) and every run is `--no-open` (no local alarm/browser) — the Echo Dot plays the brief instead; see *Alexa Flash Briefing* below
- **Why a guard, not StartCalendarInterval:** after the 2026-07-03 reboot, calendar events (routed through UserEventAgent-Aqua) silently stopped being delivered — launchd showed `runs = 0` with a dead event-channel port while the Mac was awake. `StartInterval` uses launchd's own timer and coalesces missed ticks on wake, so it self-heals after sleep/reboot. A `pmset` repeating wake at 5:58 AM (set 2026-07-03, survives reboots) covers the Mac-asleep case

## Garden Ambience (wake-up overlay)
`assets/garden-ambience.mp3` (6:30) is a faithful offline render of the ambient soundscape from Jackson's https://eth-garden.vercel.app/ (used with permission). It lives in `assets/` because the daily rebuild `rm -rf`'s `audio/` (that ate the first copy on 2026-08-18). At 6 AM the alarm starts it first: 45s fade-in → ~3 min solo ambience (gentle wake, −29 LUFS) → holds that level as a bed under the spoken segments (voice ≈ 8 dB above; Ben tuned this by ear — no duck) → fades out by 6:30. The alarm sequence in `daily-dashboard.sh` starts it in the background and waits 180s before the wake-up intro; if the file is missing the alarm behaves as before. Re-render with `tools/ethgarden-render.mjs` (see `tools/README.md`).

## Morning Console (God mode)
**https://tasks.benmartel.com/morning/** (password `m`) — bedside dashboard whose dials shape the next brief. Source: `console/` in this repo; deploy with `console/deploy-console.sh` (rsync to the tasks droplet, `/var/www/tasks/morning/`; state + token in `/var/www/tasks-private/`). Knobs: alarm armed / skip-once / one-time wake hour / volume; garden on-off + solo minutes; "voice weather" (layered narrate instructions); whisper-to-tomorrow (woven into the intro); poem doorway pick; tasks/comms/mirror toggles; editors for refrain, fixed intro, affirmation pool.

Flow: the dashboard saves to the droplet; `~/.claude/scripts/brief-console-sync.sh` (called by the guard every tick from 5 AM until the brief fires, and by the script at run start) pulls state → materializes `~/.claude/brief-console.json` + `daily-brief-wakeup.state` + `daily-brief-start-override`, then acks so the dashboard shows MAC LINK status. Token: `BRIEF_CONSOLE_TOKEN` in `~/.claude/.env` (mirrored in the droplet's `morning-config.php`). One-shots (whisper, doorway, wake hour, skip) are stamped with the morning they target and expire on their own.

v2 additions: **Suggestions** (scrollable curated gallery — voice weathers, whisper templates, doorways, clock/garden recipes, liturgy variants, full combos — one-tap apply); **Revisions** (🔒 hold freezes everything server-side — saves/restores return 423 until released; named versions snapshot the reusable knobs, restorable/deletable; "Original" restores factory defaults); **Preview** (a computed timeline of tomorrow + per-section generated samples — intro/poem/mirror via the Anthropic API from the droplet, same prompts/model as mornings, plus "hear it" TTS through OpenAI shimmer with the current voice weather applied). Preview keys live in the droplet's `morning-config.php` (pushed by `deploy-console.sh` from `~/.claude/.env`). Versions in `/var/www/tasks-private/morning-versions.json`.

## Alexa Flash Briefing (Echo mode)
The bedroom speaker (B06 Pro) is normally owned by Ben's **Echo Dot** — one Bluetooth audio slot, so the Mac's 6 AM claim always lost (Aug 24–26 all fell back to office speakers at full volume). Echo mode ends the fight: the **Echo plays the brief itself** as a private Alexa flash briefing, through the speaker it already holds.

- Every run builds `audio/wakeup-echo.mp3` — the full wake-up in one file: garden ambience from t=0 (envelope baked into the asset), voice entering after the solo, native levels (`amix normalize=0` ≙ the live alarm's two afplays) — plus `alexa-feed.json` at the repo root (what Amazon polls; cache-busted streamUrl because Pages caches 10 min)
- Ben's private flash-briefing skill (Amazon dev console, kept in development mode = his account only) points at `https://bdmartel.github.io/daily-brief/alexa-feed.json`; a 6:00 AM Alexa routine (**News** action, bedroom Echo) plays it
- **Toggle:** `echo on > ~/.claude/daily-brief-echo-mode` (anything else / absent = off). ON ⇒ guard starts 20 min before target (5:40 default) and always `--no-open`; push lands ~5:45, live well before 6:00. OFF ⇒ behavior identical to pre-Echo days (feed still builds, just lags)
- **Flip order matters:** create skill → voice-test ("Alexa, play my flash briefing") → create the 6:00 routine → *then* flip the flag. Flag without routine = silent morning; routine without flag = yesterday's brief at 6:00 plus the office alarm at ~6:05
- Console knobs in Echo mode: garden on/off + solo minutes shape the mix; **alarm-off / skip-today swap the feed to `assets/alexa-silence.mp3`** (Echo wakes no one); volume = the Echo's own (set it in the routine); a one-time wake-hour override moves the build, but the **Alexa routine time must be moved by hand** in the app
- Caveats: flash-briefing items cap at 10 min (script shrinks the garden solo to keep total ≤ 9:30); pmset wake is still 5:58 — a Mac asleep at 5:40 runs at 5:58 and 6:00 gets yesterday's brief (fix: `sudo pmset repeat wakeorpoweron MTWRFSU 05:38:00`)

## Manual Run
```bash
~/.claude/scripts/daily-dashboard.sh          # full run, opens browser
~/.claude/scripts/daily-dashboard.sh --no-open # generate only, no browser
```

## Debugging
```bash
tail -50 ~/.claude/logs/daily-dashboard.log      # run output (guard markers + script output)
cat ~/.claude/daily-brief-lastrun                # did today run? "YYYY-MM-DD done" or "fail N"
launchctl list | grep daily-dashboard            # agent loaded?
launchctl print gui/501/com.claude.daily-dashboard | grep -E 'runs|state|interval'
launchctl kickstart gui/501/com.claude.daily-dashboard   # force a tick now (guard decides if a run is due)
```
To force a re-run today: delete `~/.claude/daily-brief-lastrun`, then kickstart (or wait ≤2 min).

## Archive
Previous briefs stored in `archive/YYYY-MM-DD.html` with audio in `archive/YYYY-MM-DD-audio/`.
