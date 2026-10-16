# Daily Brief

Auto-generated daily audio briefing. Runs at 6 AM via macOS launchd. Deploys to GitHub Pages, opens in browser, plays intro audio.

## How It Works
1. **Input:** `~/.claude/daily-summaries/YYYY-MM-DD.md` (activity logs written by Claude Code chat logger)
2. **Generation:** `~/.claude/scripts/daily-dashboard.sh` reads yesterday's summary, sends to Claude API, builds HTML + TTS audio
3. **Output:** `index.html` committed and pushed here; the sounds go to Cloudflare (see *Sounds on Cloudflare*)
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
- **Pause for N days:** `echo YYYY-MM-DD > ~/.claude/daily-brief-pause-until` — through that date inclusive there is no wake-up audio (no local alarm; in Echo mode the feed points at `assets/alexa-silence.mp3`). The brief still builds and deploys. The file removes itself on the first run after the date, so it resumes on its own. Lives outside the console sync, which rewrites the skip/enabled state every tick. When pausing for a morning that is only hours away, also point `alexa-feed.json` at the silence file and push, in case the Mac oversleeps 5:40 and the Echo fetches the old feed at 6:00.
- **Echo mode** (`~/.claude/daily-brief-echo-mode` contains `on`): start shifts **20 min earlier** (default 5:40) and every run is `--no-open` (no local alarm/browser) — the Echo Dot plays the brief instead; see *Alexa Flash Briefing* below
- **Why a guard, not StartCalendarInterval:** after the 2026-07-03 reboot, calendar events (routed through UserEventAgent-Aqua) silently stopped being delivered — launchd showed `runs = 0` with a dead event-channel port while the Mac was awake. `StartInterval` uses launchd's own timer and coalesces missed ticks on wake, so it self-heals after sleep/reboot. A `pmset` repeating wake at 5:58 AM (set 2026-07-03, survives reboots) covers the Mac-asleep case

## What Is Spoken (2026-09-22)
Only the **poetry lesson** (`poem-preface.mp3`) and the **poem** (`poem.mp3`) are narrated. The wake-up intro, tasks, comms recap, mirror moment, and the page's own "Listen to today's brief" narration (intro + one clip per card + outro) are generated as **text only** — they still appear on the page, they are just never rendered to audio (Ben: "put all the other items other than the poem and poetry lesson on not narrated"). The wake-up is therefore: the morning's field recording solo → lesson → poem (read twice, "So — up!" once at the end) → the recording fades. The poem's two readings are also saved apart (`poem-first.mp3`, `poem-again.mp3`) for the page's poem · lesson · poem button (see *Archive*).
- Change the spoken set without editing the script: `~/.claude/daily-brief-spoken.txt` holds a space-separated list in play order (`wakeup-intro poem-preface poem tasks comms affirmations`); delete it to return to lesson + poem.
- `echo on > ~/.claude/daily-brief-page-narration` turns the page narration back on (it costs about a third of the brief's OpenAI spend; the top "Listen" bar and the per-card play buttons hide themselves while it is off).
- The page's lower-right wake-up player lists the spoken segments plus "This morning's sound" (the day's field recording on its own).

## Sound of the Morning (wake-up bed: real field recordings, 2026-10-02)
The sound under and before the voice is a **real field recording, different every morning** (Ben, 2026-10-02: "the digitally created sounds are artificial sounding ... pull up some actual sound recordings ... an element of intrigue behind the voice. I found it was competing with the voice"). It replaced the synthesized scenes of `tools/soundscape.py` (Sep 22 – Oct 1; retired, file kept for reference).
- **Catalog:** `tools/fieldbeds.json`, 26 recordings, **CC0 or CC BY only** (the mix is public on Pages, and CC BY requires the credit the page shows; no NC/SA). Rain (Sri Lanka jungle, Bailey Island ME cabin roof, tin roof at dawn, French barn, Shiga summer storm), moving water (Jadwiżanka PL, Transylvania snowmelt + half-frozen stream, east Iceland, Gatineau brook under snow, Saas-Fee glacier water, a winter waterfall, snowmelt woods), shores (Hallsands, Sooke BC, Borax Lake OR, a lake near Leipzig), night and creatures (horned owls, barred owls on the Neches, Brazil and Florida frogs, dusk at the Alentejo menhir, Swiss cows, a beehive), the suikinkutsu at Enkō-ji in Kyoto, a fireplace. Each entry: caption, recordist, license, source page, Freesound HQ-preview URL, `end` (only the first ~4–12 min is used), high-pass, and `months` when seasonal (cicadas in summer, frozen stream in winter, fireplace Oct–Apr). Chosen from ~1,600 search results by measuring spikes, rumble, clipping and speech-band energy, and screened for voices (by description; Whisper is useless for this, it hallucinates on all nature audio).
- **Cache:** `assets/field/` (gitignored, ~300 MB). `python3 tools/fieldbed.py --fetch` re-downloads anything missing (Range requests for just the part the catalog uses; Freesound's CDN gives ~80 KB/s per connection, so a full refetch is slow). A morning never waits on the network: the pick only takes recordings already cached.
- **Pick:** at build time, in-season recordings minus the most recent picks in `~/.claude/daily-brief-bed-history.txt` (up to 14 mornings, always leaving 3 to choose from). Each render is a seeded random stretch of the recording, so a repeat is a different stretch. The page names, links and credits it under the poem; `audio/bed.txt` = `id|caption|seed|credit|source`.
- **Shaping** (`tools/fieldbed.py`): high-pass; events more than 8 dB over the body softened 3:1 (crows, a moo); −29 LUFS (Ben's ear-tuned level; voice ≈ −22); clicks and pops held under −12 dBFS; 45 s fade-in, solo for the console's garden-solo seconds, 20 s fade-out.
- **Voice pocket:** while the voice plays, the bed crossfades to a copy with the 1–4 kHz speech band cut 6 dB; the level stays put. Why: the synthesized brook Ben said was "competing with the voice" had 46% of its energy at 1–4 kHz and 78% of its flutter at syllable rate (3–12 Hz), so the ear kept hearing talk in it; the garden he liked had 0% there. Knob: `~/.claude/daily-brief-bed-pocket` = `<carve dB> <duck dB>` (default `6 0`; `0 0` = no pocket). Ben rejected an 8 dB duck in August, so don't add one without asking.
- Console knobs still apply: garden on/off = bed on/off; solo minutes = how long the sound plays alone before the lesson.
- **Listen / change:** `python3 tools/fieldbed.py --list`; preview one with `python3 tools/fieldbed.py --render <id> --seconds 90 --out /tmp/x.wav`. Drop one: delete its catalog entry. Add one: append an entry (Freesound `…-hq.ogg` preview URL, CC0 or CC BY), then `--fetch`.
- **Fallback:** if no recording renders, the fixed `assets/garden-ambience.mp3` plays and the log says so (`/tmp/fieldbed.err` has the reason).

## Sounds on Cloudflare (2026-10-16)
Ben: "store all sounds ... so space is less of a concern", then picked "Cloudflare + shrink" from the free options. GitHub Pages had 1.3 GB of audio against its 1 GB site limit, and the droplet had only 1.2 GB free, so every sound now lives on a Cloudflare Worker with static assets: **[brief-sounds.bdmartel.workers.dev](https://brief-sounds.bdmartel.workers.dev)** (free plan: 20,000 files, 25 MB each, no storage or bandwidth bill; account bdmartel@gmail.com, wrangler OAuth login on this Mac, wrangler installed under nvm).
- **Paths:** `m/<morning>/<file>.mp3` for mornings from Oct 16 on; `a/<folder>/<file>.mp3` for the older archive folders by their folder name (their morning can't always be told: on 7 mornings two folders share a page title); `latest/<file>.mp3` redirects to the newest morning (wakeup.html and the Daily Garden skill's fallback use it).
- **Shrunk:** mono voice files at 48 kbps (a third of 128, no audible change in speech), stereo mixes at 96 kbps. The originals stay on the Mac in `audio/` and `archive/<name>-audio/`; `*.mp3` there is gitignored. `sounds/` (gitignored) holds the shrunk copies (`sounds/public`), the Worker config and `online.json` (what is confirmed uploaded).
- **Each morning:** `tools/sounds.py publish --today <date>` runs right before the commit. It shrinks what's new, runs `wrangler deploy`, writes `audio/.published` (the archive copies it along), and re-points `index.html` (including the Last-5 card), `archive/*.html`, `alexa-feed.json` (the Echo's stream) and `wakeup.html`. If the upload fails, today's links stay relative, the script force-adds today's mp3s to GitHub, and the next run uploads and re-points them. Log: `/tmp/sounds.log`.
- **By hand:** `python3 tools/sounds.py rewrite` re-points pages for what's online; `sync` only shrinks.

## Weekly Poetry Workshop (poetry.benmartel.com, 2026-10-15)
Ben: "make a sort of lesson roundup weekly for the poems that gets published once a week for me to sit down and really get inspired to write some of my own poetry ... visually laid out ... divided in 7 parts, with further examples, an expound of the week's poem lessons". Live at [poetry.benmartel.com](https://poetry.benmartel.com) (public, noindex, Utility look; past weeks under `/weeks/<end>.html`).
- **What a week is:** a cover (what the week added up to, the seven tools, one big prompt that combines them) and one part per morning: the technique in a sentence, that morning's lines with the technique marked and numbered, *Go deeper* (what it really does, the usual beginner mistake, how it works with an earlier tool), *Further examples* (two real poems plus one written for the lesson), *How to use it* (numbered steps), *Try it* (a 15-minute exercise), a draft checklist, and the one rule to keep in the bottom band. Each part has a poem, lesson, poem player. Prints one part per page.
- **How it is made:** `tools/poem_roundup.py` gathers the seven mornings (each folder's `lesson.json`: technique, lesson, poem), asks Claude (`claude-opus-5-5`) for the week as JSON, then checks it before rendering: excerpt line numbers must exist, marked words must be on that line, and real-poet quotes can only come from `tools/anthology.json` by id and line numbers, printed straight from that file, so every quoted line is verbatim. Anything that fails a check is dropped, not guessed. Data: `poetry/data/<end>.json` (in git). Pages: `poetry/site/` (gitignored), uploaded by `poetry/deploy.sh` to `/var/www/poetry/app` on the droplet.
- **lesson.json:** the morning script writes `audio/lesson.json` after narrating the lesson (archived with the audio). Mornings before Oct 16 were transcribed once from `poem-preface.mp3` with local whisper; the lesson sometimes teaches the nearest technique instead of the scheduled one, and the workshop follows what was taught.
- **Schedule:** the guard calls `poem_roundup.py --if-due` once today's brief is done. A week is due on Sunday (or the first run after) for the Sunday to Saturday just ended, unless a saved week overlaps it. The first week (Oct 9 to 15) was built by hand on Oct 15, so the next is Sunday Oct 25 (Oct 18 to 24). State: `~/.claude/poem-roundup-state` (3 attempts a day); log: `~/.claude/logs/poem-roundup.log`.
- **By hand:** `python3 tools/poem_roundup.py --end YYYY-MM-DD` builds and deploys the seven mornings ending that day (one API call). `--render` rebuilds every page from the saved data with no API call. `--if-due` builds for real when a week is due, so don't run it to test.
- **Sounds:** the play buttons use each morning's split readings on Cloudflare (see *Sounds on Cloudflare*). The brief's Last-5 card links here.

## Garden Ambience (the fixed take, now the fallback)
`assets/garden-ambience.mp3` (6:30) is a faithful offline render of the ambient soundscape from Jackson's https://eth-garden.vercel.app/ (used with permission). It lives in `assets/` because the daily rebuild `rm -rf`'s `audio/` (that ate the first copy on 2026-08-18). At 6 AM the alarm starts it first: 45s fade-in → ~3 min solo ambience (gentle wake, −29 LUFS) → holds that level as a bed under the spoken segments (voice ≈ 8 dB above; Ben tuned this by ear — no duck) → fades out by 6:30. The alarm sequence in `daily-dashboard.sh` starts it in the background and waits 180s before the wake-up intro; if the file is missing the alarm behaves as before. Re-render with `tools/ethgarden-render.mjs` (see `tools/README.md`).

## Morning Console (God mode)
**https://tasks.benmartel.com/morning/** (password `m`) — bedside dashboard whose dials shape the next brief. Source: `console/` in this repo; deploy with `console/deploy-console.sh` (rsync to the tasks droplet, `/var/www/tasks/morning/`; state + token in `/var/www/tasks-private/`). Knobs: alarm armed / skip-once / one-time wake hour / volume; garden on-off + solo minutes; "voice weather" (layered narrate instructions); whisper-to-tomorrow (woven into the intro); poem doorway pick; tasks/comms/mirror toggles; editors for refrain, fixed intro, affirmation pool.

Flow: the dashboard saves to the droplet; `~/.claude/scripts/brief-console-sync.sh` (called by the guard every tick from 5 AM until the brief fires, and by the script at run start) pulls state → materializes `~/.claude/brief-console.json` + `daily-brief-wakeup.state` + `daily-brief-start-override`, then acks so the dashboard shows MAC LINK status. Token: `BRIEF_CONSOLE_TOKEN` in `~/.claude/.env` (mirrored in the droplet's `morning-config.php`). One-shots (whisper, doorway, wake hour, skip) are stamped with the morning they target and expire on their own.

v2 additions: **Suggestions** (scrollable curated gallery — voice weathers, whisper templates, doorways, clock/garden recipes, liturgy variants, full combos — one-tap apply); **Revisions** (🔒 hold freezes everything server-side — saves/restores return 423 until released; named versions snapshot the reusable knobs, restorable/deletable; "Original" restores factory defaults); **Preview** (a computed timeline of tomorrow + per-section generated samples — intro/poem/mirror via the Anthropic API from the droplet, same prompts/model as mornings, plus "hear it" TTS through OpenAI shimmer with the current voice weather applied). Preview keys live in the droplet's `morning-config.php` (pushed by `deploy-console.sh` from `~/.claude/.env`). Versions in `/var/www/tasks-private/morning-versions.json`.

## Alexa Flash Briefing (Echo mode)
The bedroom speaker (B06 Pro) is normally owned by Ben's **Echo Dot** — one Bluetooth audio slot, so the Mac's 6 AM claim always lost (Aug 24–26 all fell back to office speakers at full volume). Echo mode ends the fight: the **Echo plays the brief itself** as a private Alexa flash briefing, through the speaker it already holds.

- Every run builds `audio/wakeup-echo.mp3` — the full wake-up in one file: the morning's bed from t=0 (envelope baked in), voice entering after the solo, native levels (`amix normalize=0` ≙ the live alarm's two afplays) — plus `alexa-feed.json` at the repo root (what Amazon polls). Since 2026-10-16 its streamUrl is the morning's own file on Cloudflare (`m/<date>/wakeup-echo.mp3`, unique per day, so no cache-buster is needed); on a failed upload it stays on GitHub with a cache-buster
- Ben's private flash-briefing skill (Amazon dev console, kept in development mode = his account only) points at `https://bdmartel.github.io/daily-brief/alexa-feed.json`; a 6:00 AM Alexa routine (**News** action, bedroom Echo) plays it
- **Toggle:** `echo on > ~/.claude/daily-brief-echo-mode` (anything else / absent = off). ON ⇒ guard starts 20 min before target (5:40 default) and always `--no-open`; push lands ~5:45, live well before 6:00. OFF ⇒ behavior identical to pre-Echo days (feed still builds, just lags)
- **Flip order matters:** create skill → voice-test ("Alexa, play my flash briefing") → create the 6:00 routine → *then* flip the flag. Flag without routine = silent morning; routine without flag = yesterday's brief at 6:00 plus the office alarm at ~6:05
- Console knobs in Echo mode: garden on/off + solo minutes shape the mix; **alarm-off / skip-today swap the feed to `assets/alexa-silence.mp3`** (Echo wakes no one); volume = the Echo's own (set it in the routine); a one-time wake-hour override moves the build, but the **Alexa routine time must be moved by hand** in the app
- Caveats: flash-briefing items cap at 10 min (script shrinks the garden solo to keep total ≤ 9:30); pmset wake is still 5:58 — a Mac asleep at 5:40 runs at 5:58 and 6:00 gets yesterday's brief (fix: `sudo pmset repeat wakeorpoweron MTWRFSU 05:38:00`)

### "Daily Garden" — zero-speech custom skill (the preferred 6 AM player)
Flash briefings always speak ("Here's your flash briefing" + a required In/From preamble). The **Daily Garden** custom skill (ID `amzn1.ask.skill.2400c000-1fef-4296-97fc-c4fb8e2c7fb4`, In Dev, private) plays the same audio with **zero speech**: its endpoint answers `LaunchRequest` with only an `AudioPlayer.Play` directive (no `outputSpeech`), so playback starts cold on the garden fade-in.
- **Endpoint:** `console/alexa-garden.php` in this repo, deployed to the tasks droplet at `/var/www/morning/alexa-garden.php` (= https://tasks.benmartel.com/morning/alexa-garden.php; `console/deploy-console.sh` rsyncs the whole folder, so console deploys keep it live). It reads `alexa-feed.json` for the morning's stream URL — so skip/off mornings automatically play the silence file. Pause/Stop → `AudioPlayer.Stop`; Resume/`PlayGardenIntent` → replay. Dev-only skill ⇒ no request-signature verification.
- **Trigger:** Alexa routine custom action **"open daily garden"** (or say it). Invocation name: `daily garden`.
- **Built via SMAPI**, not the console UI (the create-skill wizard rendered an empty shell under scripted control): `ask-cli` is installed globally; fresh tokens via `ask util generate-lwa-tokens` (needs `~/.ask/cli_config` to exist; consent auto-approves after first grant). Simulation-verified: spoken response `[]`, Play directive present.
- The flash-briefing skill stays configured as **fallback** — if Alexa+ ever breaks routine→custom-skill audio, switch the routine action back to News → Flash Briefing.

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
Previous briefs stored in `archive/YYYY-MM-DD.html` with audio in `archive/YYYY-MM-DD-audio/` (every morning's audio is kept and online). **Folder dates are the day the brief was archived, i.e. the morning AFTER that audio played**: the archive step reads the old page title with `grep -oP`, which macOS grep lacks under launchd, so it falls back to today's date. Don't "fix" that without migrating the names: the first fixed run would find its folder already taken and skip archiving the audio.

**Last five mornings** (Ben, 2026-10-15: "keep the last 5 online instead of one (the audio bits)"): a card under the poem lists this morning plus the four before it, each with the 6 AM wake-up as the Echo played it, the lesson, the poem and the sound (captioned). `tools/recent_mornings.py` fills the `<!--LAST_FIVE_MORNINGS-->` marker just before the commit (only files that exist get a button; a folder's morning = its archived page title + 1 day). Buttons hand that morning's tracks to the lower-right wake-up player; starting the player fresh goes back to today. The archive step also rewrites the card's `"audio/` and `"archive/` paths so archived pages still play. A refresh (re-running the tool on a page that already has the card) replaces the card between its `<!--last-five-mornings-->` comments.
- **▶ poem · lesson · poem** (Ben, 2026-10-15: "give an option where it's POEM, LESSON, POEM as a way to digest it"): the poem once, the lesson, then the poem again ending on "So — up!", which still comes only once. It plays `poem-first.mp3` (one reading, no closer), `poem-preface.mp3`, `poem-again.mp3` (one reading + closer). The morning script writes both pieces from the takes it already has. `tools/poem_split.py <audio folder>` cuts them out of an existing `poem.mp3` (it finds where the take starts over; it worked on all 32 doubled mornings since Sep 14 and leaves single-reading poems alone); Oct 11–15 were cut that way. A morning without the pieces simply has no button.
