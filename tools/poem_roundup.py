#!/usr/bin/env python3
"""poem_roundup.py: the weekly poetry workshop at poetry.benmartel.com (2026-10-15).

Ben, 2026-10-15: "make a sort of lesson roundup weekly for the poems that gets published once a
week for me to sit down and really get inspired to write some of my own poetry, lean in on what's
been learned, how to utilize it, and the lesson should be visually laid out as well, divided in 7
parts, with further examples, an expound of the week's poem lessons".

Every morning's lesson (poem-preface) teaches one technique on that morning's poem. Once a week this
gathers seven mornings (poem, lesson, technique) and builds a workshop page with one part per
morning: the technique in a sentence, the morning's lines with the technique marked, the lesson
taken further, more examples (real poems quoted only from tools/anthology.json, so every quoted line
is verbatim, plus a fresh example), steps for using it, an exercise and a checklist for the draft.

  poem_roundup.py --end 2026-10-15     build the week ending that morning and deploy it
  poem_roundup.py --if-due             what the guard runs: Sundays (or the first run after), the
                                       week Sunday to Saturday, unless the last one overlaps it
  poem_roundup.py --render             re-render every saved week from poetry/data (no API call)
  --collect                            only gather the week; --no-deploy skips the upload

Each morning's lesson comes from lesson.json in its audio folder (the morning script writes it;
older mornings are transcribed once from poem-preface.mp3). Data: poetry/data/<end>.json (in git).
Site: poetry/site/ (gitignored), uploaded by poetry/deploy.sh.
"""
import argparse, datetime, html, json, os, re, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import recent_mornings  # noqa: E402  (morning_of: an archive folder's morning)

DATA = os.path.join(REPO, 'poetry', 'data')
SITE = os.path.join(REPO, 'poetry', 'site')
DEPLOY = os.path.join(REPO, 'poetry', 'deploy.sh')
ANTHOLOGY = os.path.join(HERE, 'anthology.json')
STATE = os.path.expanduser('~/.claude/poem-roundup-state')
LOCK = os.path.expanduser('~/.claude/poem-roundup.lock')
MODEL = 'claude-opus-5-5'
SITE_URL = 'https://poetry.benmartel.com'
BRIEF_URL = 'https://bdmartel.github.io/daily-brief'
SESSION_URL = 'https://claude.ai/code/session_01NbSUjahHck8yBftYTDzmE1'
# Where each morning's sounds are served. Today they are on GitHub Pages (archive/<name>-audio/).
GH = BRIEF_URL + '/'

# Same list and order as PREFACE_TECHNIQUES in ~/.claude/scripts/daily-dashboard.sh; the morning
# of day D teaches TECHNIQUES[(day of year + 5) % 12]. Only used for mornings before lesson.json.
TECHNIQUES = [
    "entering mid-action, with no setup at all",
    "letting one plain object carry the feeling",
    "the turn — the exact line where picture becomes meaning, and how the poem earns it",
    "line breaks — where the breath falls, and what the break withholds for a beat",
    "sound — the consonants and vowels doing quiet work, worth saying aloud",
    "verbs over adjectives — how the action words carry the weight",
    "the second person — how 'you' pulls the reader into the room",
    "withholding — what the poem refuses to name or explain, and why that works",
    "the exit — leaving on an image instead of a statement",
    "scale — moving between the tiny and the large in a few lines",
    "repetition with a difference — a word or shape returning changed",
    "time — how the poem moves through it, or holds still",
]
KEYS = ['mid-action', 'plain-object', 'turn', 'line-breaks', 'sound', 'verbs', 'second-person',
        'withholding', 'exit', 'scale', 'repetition', 'time']


# ---------------------------------------------------------------- the week's mornings

def page_morning(page):
    """The morning a brief page played: its title's date + 1 day (the title names the day summarized)."""
    try:
        with open(page, encoding='utf-8') as f:
            m = re.search(r'<title>Daily Brief - ([A-Za-z]+ \d{1,2}, \d{4})</title>', f.read(4096))
        if m:
            return datetime.datetime.strptime(m.group(1), '%B %d, %Y').date() + datetime.timedelta(days=1)
    except (OSError, ValueError):
        pass
    return None


def locate(day):
    """Folder, page and audio URL bases for one morning, or None if it isn't on disk."""
    if page_morning(os.path.join(REPO, 'index.html')) == day:
        # This morning's sounds sit in audio/ until the next run archives them to
        # archive/<next run's date>-audio/ (see recent_mornings.py), so offer both.
        nxt = (day + datetime.timedelta(days=1)).isoformat()
        return {'folder': os.path.join(REPO, 'audio'), 'page': os.path.join(REPO, 'index.html'),
                'bases': [GH + f'archive/{nxt}-audio/', GH + 'audio/']}
    for d in sorted(os.listdir(os.path.join(REPO, 'archive')), reverse=True):
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}-audio', d) and recent_mornings.morning_of(REPO, d[:-6]) == day:
            return {'folder': os.path.join(REPO, 'archive', d),
                    'page': os.path.join(REPO, 'archive', d[:-6] + '.html'),
                    'bases': [GH + f'archive/{d}/']}
    return None


def poem_from_page(page):
    with open(page, encoding='utf-8') as f:
        s = f.read()
    i = s.find('class="poem-card"')
    m = re.search(r'<div style="font-family:Georgia[^>]*>(.*?)</div>', s[i:], re.S) if i >= 0 else None
    return html.unescape(m.group(1)).strip() if m else ''


CLOSER = re.compile(r'^[\s"“”]*so\s*[—–\-,]*\s*up\s*[.!?…"“”]*\s*$', re.I)


def norm(t):
    return re.sub(r'[^a-z0-9]+', ' ', t.lower()).strip()


def tidy_poem(text):
    """The poem as it should have read: the closer once, at the end. On 7 of 33 mornings (Sep 19 to
    Oct 14) the verse model wrote its own ending too, so the page showed the motivator and So, up
    twice. Drop every closer line but the last, and verse lines that repeat the closing motivator."""
    lines = text.split('\n')
    closers = [i for i, t in enumerate(lines) if CLOSER.match(t)]
    if len(closers) < 2:
        return text
    last = closers[-1]
    motivator = norm(' '.join(t for t in lines[closers[-2] + 1:last] if t.strip()))
    keep = [t for i, t in enumerate(lines) if i == last or not CLOSER.match(t)]
    cut = keep.index(lines[last]) if lines[last] in keep else len(keep)
    head, tail = keep[:cut], keep[cut:]
    body = [t for t in head]
    # the motivator's last appearance (just before the closer) stays; an earlier copy goes
    end = len(body)
    while end and not body[end - 1].strip():
        end -= 1
    start = end
    while start and body[start - 1].strip():
        start -= 1
    if motivator and norm(' '.join(body[start:end])) == motivator:
        k = start
        while k and not body[k - 1].strip():
            k -= 1
        for a in range(k, -1, -1):
            for b in range(a + 1, k + 1):
                if norm(' '.join(t for t in body[a:b] if t.strip())) == motivator and \
                        all(not t.strip() for t in body[b:k]):
                    body = body[:a] + body[start:end] + body[end:]
                    k = -1
                    break
            if k < 0:
                break
    out = '\n'.join(body + tail)
    return re.sub(r'\n{3,}', '\n\n', out).strip()


_whisper = []


def transcribe(mp3):
    if not _whisper:
        import warnings
        warnings.filterwarnings('ignore')
        import whisper
        _whisper.append(whisper.load_model('small'))
    return _whisper[0].transcribe(mp3, language='en', fp16=False)['text'].strip()


def week(end, count=7):
    """The mornings from end-6 to end that exist, oldest first."""
    out = []
    for k in range(count - 1, -1, -1):
        day = end - datetime.timedelta(days=k)
        loc = locate(day)
        if not loc:
            continue
        path = os.path.join(loc['folder'], 'lesson.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                d = json.load(f)
        else:
            d = {'morning': day.isoformat(),
                 'technique': TECHNIQUES[(day.timetuple().tm_yday + 5) % 12],
                 'poem': poem_from_page(loc['page']), 'lesson': '', 'lesson_source': 'transcribed'}
            if os.path.exists(os.path.join(loc['folder'], 'poem-preface.mp3')):
                d['lesson'] = transcribe(os.path.join(loc['folder'], 'poem-preface.mp3'))
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False, indent=1)
        if not d.get('poem'):
            continue
        d['poem'] = tidy_poem(d['poem'])
        files = {f: os.path.exists(os.path.join(loc['folder'], f))
                 for f in ('poem-first.mp3', 'poem-preface.mp3', 'poem-again.mp3', 'poem.mp3')}
        d.update(date=day, bases=loc['bases'], files=files)
        out.append(d)
    return out


# ---------------------------------------------------------------- asking Claude

def api_key():
    if os.environ.get('ANTHROPIC_API_KEY'):
        return os.environ['ANTHROPIC_API_KEY']
    try:
        with open(os.path.expanduser('~/.claude/.env'), encoding='utf-8') as f:
            for line in f:
                m = re.match(r'\s*(?:export\s+)?ANTHROPIC_API_KEY\s*=\s*["\']?([^"\'\s]+)', line)
                if m:
                    return m.group(1)
    except OSError:
        pass
    sys.exit('poem_roundup: no ANTHROPIC_API_KEY')


def verse(lines):
    """Indexes of the lines that count: blank stanza-break lines get no number."""
    return [i for i, t in enumerate(lines) if t.strip()]


def numbered(lines):
    out, n = [], 0
    for t in lines:
        if t.strip():
            n += 1
            out.append(f'{n:>3}  {t}')
        else:
            out.append('')
    return '\n'.join(out)


SYSTEM = """You are a plainspoken poetry-writing teacher. You write Ben's weekly workshop, the kind of \
lesson he works through at a table with a pen. Ben is a beginner who is building a farming life in the \
New Hampshire hills and wants to learn to write poems of his own. Every morning this week he heard a \
short poem and a spoken lesson of 100 to 150 words that taught one technique on it. The workshop takes \
those seven lessons further: what each one is really doing, more examples, how to use it, and a \
writing exercise. It should leave him wanting to write."""

SPEC = """Write the workshop as one JSON object, nothing before or after it, in this shape:
{
  "intro": "2 or 3 sentences: what this week's seven lessons add up to, and how the techniques work together",
  "week_prompt": "one writing exercise that uses two or three of this week's techniques at once, at most 40 words",
  "parts": [ one object per morning, in the order given:
    {
      "technique": "2 to 4 words naming the technique the lesson actually taught",
      "definition": "one plain sentence, at most 20 words",
      "excerpt": [first_line, last_line],
      "marks": [ {"line": n, "words": "exact words copied from line n", "note": "at most 10 words"} ],
      "deeper": ["paragraph", "paragraph", "paragraph"],
      "examples": [ {"poem": "anthology id", "lines": [first_line, last_line], "note": "one or two sentences"} ],
      "fresh": {"lines": ["line", "line"], "note": "one sentence"},
      "steps": [ {"head": "2 to 4 words", "detail": "at most 22 words"} ],
      "exercise": "one writing task for 10 to 15 minutes, at most 35 words",
      "checklist": ["at most 12 words"],
      "keep": "the one rule to remember, at most 8 words"
    }
  ]
}

Rules for each part:
- technique: follow what the lesson actually taught. The lesson sometimes swapped the scheduled technique for the nearest one the poem really uses.
- excerpt: line numbers from that morning's poem (numbered below), 3 to 8 lines that show the technique best.
- marks: 2 to 4 marks inside the excerpt. "words" must be copied exactly, character for character, from that line, and be short (1 to 6 words). The note says what the marked words are doing.
- deeper: 2 or 3 short paragraphs, 150 to 230 words in all, that go well past the morning lesson: what the technique is really doing to a reader or listener and why it works; the most common beginner mistake with it and how to fix it; and how it works together with another technique from earlier in this week, by name (lean on what he has already learned). Point at the morning poem's actual words.
- examples: exactly 2, from the anthology only, by id and line numbers, at most 8 lines each, from 2 different poems that clearly show this technique. The note says exactly what to notice in those lines. Never use the same anthology poem twice in the workshop.
- fresh: 3 to 6 lines you write now that show the technique cleanly, set in Ben's world (barn, woodpile, stove, sheep, garden beds, frost, a truck, the hills). Not a copy of the morning poem. The note says what it does.
- steps: 3 or 4 steps, in order, for using the technique while drafting or revising.
- exercise: one specific task with a concrete subject from his life. checklist: 3 or 4 checks for the draft.
- keep: short, plain, worth taping above the desk.

Rules for all prose:
- Plain, literal sentences, mostly short. Speak to him as you. No jargon unless you define it in the same sentence.
- When you mention words from a poem, wrap them in double square brackets, like [[throws]]. Never use quotation marks of any kind.
- Never use an em dash or an en dash anywhere. Use commas, periods or colons.
- No gushing, no exclamation marks, no talk about the magic of words or painting pictures.
"""


def build_prompt(days, anthology, last):
    parts = []
    for i, d in enumerate(days):
        lines = d['poem'].split('\n')
        parts.append(
            f"PART {i + 1}: {d['date']:%A %B} {d['date'].day}\n"
            f"Scheduled technique: {d['technique']}\n"
            f"The morning lesson ({'transcribed from the audio, so a few words may be off' if d.get('lesson_source') == 'transcribed' else 'as spoken'}):\n"
            f"{d['lesson'] or '(no lesson that morning; teach the scheduled technique on this poem)'}\n"
            f"The morning poem, numbered:\n{numbered(lines)}")
    anth = []
    for p in anthology:
        anth.append(f"id: {p['id']} | {p['poet']}, {p['title']} ({p['year']}) | good for: {', '.join(p.get('good_for', []))}\n"
                    f"{numbered(p['lines'])}")
    avoid = ''
    if last:
        used = sorted({e['poem'] for prt in last.get('parts', []) for e in prt.get('examples', [])})
        ex = [prt.get('exercise', '') for prt in last.get('parts', [])]
        avoid = ("\n\nLAST WEEK'S WORKSHOP already used these anthology poems; choose others: "
                 + ', '.join(used) + "\nLast week's exercises, so yours are different:\n- " + '\n- '.join(ex))
    return (SPEC + '\n\nTHE WEEK\n\n' + '\n\n'.join(parts)
            + '\n\nTHE ANTHOLOGY (public-domain poems; quote only these, by id and line numbers)\n\n'
            + ('\n\n'.join(anth) if anth else '(empty: leave "examples" as an empty list)') + avoid)


def ask(system, user, max_tokens=48000):
    body = json.dumps({'model': MODEL, 'max_tokens': max_tokens, 'system': system,
                       'messages': [{'role': 'user', 'content': user}]}).encode()
    req = urllib.request.Request('https://api.anthropic.com/v1/messages', data=body, headers={
        'content-type': 'application/json', 'x-api-key': api_key(), 'anthropic-version': '2023-06-01'})
    with urllib.request.urlopen(req, timeout=900) as r:
        d = json.load(r)
    text = ''.join(b.get('text', '') for b in d.get('content', []) if b.get('type') == 'text')
    try:  # the last reply, kept for when something goes wrong
        with open(os.path.join(REPO, 'poetry', 'last-reply.json'), 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
    except OSError:
        pass
    return text, d.get('stop_reason'), d.get('usage', {})


def parse(text):
    a, b = text.find('{'), text.rfind('}')
    return json.loads(text[a:b + 1])


# ---------------------------------------------------------------- checking what came back

def clean_prose(s):
    """The Utility rules: no em or en dashes and no quotation marks in copy."""
    s = str(s or '').strip()
    s = re.sub(r'\s*[—–]\s*', ', ', s)
    s = re.sub(r'[“"]([^”"\n]{1,80})[”"]', r'[[\1]]', s)
    return s.replace('“', '').replace('”', '').replace('"', '')


def clean_line(s):
    return re.sub(r'\s*[—–]\s*', ', ', str(s or '')).rstrip()


def span(pair, n, longest):
    try:
        a, b = int(pair[0]), int(pair[1])
    except (TypeError, ValueError, IndexError):
        return None
    a, b = max(1, a), min(n, b)
    if a > b:
        return None
    return a, min(b, a + longest - 1)


def check(raw, days, anthology):
    """Keep only what can be shown truthfully: real line numbers, words that are really on the line,
    anthology quotes that exist. Everything else is dropped, not guessed."""
    poems = {p['id']: p for p in anthology}
    out = {'intro': clean_prose(raw.get('intro')), 'week_prompt': clean_prose(raw.get('week_prompt')), 'parts': []}
    rparts = raw.get('parts') or []
    used = set()
    for i, d in enumerate(days):
        r = rparts[i] if i < len(rparts) and isinstance(rparts[i], dict) else {}
        lines = d['poem'].split('\n')
        V = verse(lines)
        ex = span(r.get('excerpt') or [], len(V), 9) or (1, min(len(V), 6))
        marks = []
        for m in (r.get('marks') or [])[:4]:
            words, note = str(m.get('words', '')).strip(), clean_prose(m.get('note'))
            if not words:
                continue
            try:
                ln = int(m.get('line'))
            except (TypeError, ValueError):
                ln = 0
            if not (ex[0] <= ln <= ex[1] and words in lines[V[ln - 1]]):
                ln = next((k for k in range(ex[0], ex[1] + 1) if words in lines[V[k - 1]]), 0)
            if ln:
                marks.append({'line': ln, 'words': words, 'note': note})
        examples = []
        for e in (r.get('examples') or [])[:3]:
            p = poems.get(str(e.get('poem', '')))
            if not p or p['id'] in used:
                continue
            sp = span(e.get('lines') or [], len(verse(p['lines'])), 8)
            if not sp:
                continue
            used.add(p['id'])
            examples.append({'poem': p['id'], 'lines': list(sp), 'note': clean_prose(e.get('note'))})
            if len(examples) == 2:
                break
        fresh = r.get('fresh') or {}
        out['parts'].append({
            'morning': d['date'].isoformat(),
            'technique': clean_prose(r.get('technique')) or d['technique'].split(' —')[0].split(',')[0].capitalize(),
            'definition': clean_prose(r.get('definition')),
            'excerpt': list(ex), 'marks': marks,
            'deeper': [clean_prose(p) for p in (r.get('deeper') or []) if str(p).strip()][:4],
            'examples': examples,
            'fresh': {'lines': [clean_line(t) for t in (fresh.get('lines') or [])][:8], 'note': clean_prose(fresh.get('note'))},
            'steps': [{'head': clean_prose(s.get('head')), 'detail': clean_prose(s.get('detail'))}
                      for s in (r.get('steps') or [])[:5] if isinstance(s, dict)],
            'exercise': clean_prose(r.get('exercise')),
            'checklist': [clean_prose(c) for c in (r.get('checklist') or [])[:5] if str(c).strip()],
            'keep': clean_prose(r.get('keep')),
        })
    return out


# ---------------------------------------------------------------- the page (Utility look)

CSS = """
/* Tokens: ~/.claude/design/tokens.css (utility), copied 2026-10-15. Classes: the utility section of
   components.css plus a few for this page. Black and white only. */
:root {
  color-scheme: light;
  --ink: #000000; --paper: #ffffff;
  --font: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  --frame: 3px; --rule: 1.5px;
  --bg: #ffffff; --surface: #ffffff; --surface-2: #ffffff; --border: #000000; --text: #000000; --muted: #000000;
  --accent: #000000; --accent-dim: #ffffff; --on-accent: #ffffff;
  --th-bg: #000000; --th-fg: #ffffff;
  --font-body: 'Helvetica Neue', Helvetica, Arial, sans-serif; --font-display: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  --font-mono: ui-monospace, Menlo, Consolas, monospace;
  --fs: 14px; --lh: 1.3;
  --label-transform: uppercase; --label-tracking: 0.02em; --label-weight: 700;
  --radius: 0; --radius-sm: 0; --radius-pill: 0;
  --border-w: 1.5px; --card-border-w: 3px; --shadow: none;
}
html, body { margin: 0; background: var(--bg); color: var(--text); font-family: var(--font-body); font-size: var(--fs); line-height: var(--lh); -webkit-font-smoothing: antialiased; }
a { color: var(--ink); }
.card { background: var(--surface); border: var(--card-border-w) solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow); box-sizing: border-box; }
.title { font-family: var(--font); font-weight: 700; font-size: 44px; line-height: 1; text-transform: uppercase; text-align: center; margin: 16px 8px 12px; overflow-wrap: anywhere; }
.band { background: var(--ink); color: var(--paper); font-weight: 700; text-transform: uppercase; text-align: center; font-size: 20px; line-height: 1.15; padding: 6px; }
.subhead { font-weight: 700; text-align: center; font-size: 15px; margin: 10px; }
.step { display: grid; grid-template-columns: 28px 1fr; gap: 8px; margin: 8px 16px; align-items: start; }
.step b { display: grid; place-items: center; width: 24px; height: 24px; border-radius: 50%; background: var(--ink); color: var(--paper); font-size: 14px; font-weight: 700; }
.step h4 { margin: 0; font-size: 16px; font-weight: 700; line-height: 1.25; text-transform: uppercase; }
.step p { margin: 2px 0 0; font-size: 14px; line-height: 1.3; }
.check-group { margin: 8px 16px; }
.check-group h4, .sec > h4 { display: flex; align-items: center; gap: 8px; margin: 0 0 6px; font-size: 13px; font-weight: 700; text-transform: uppercase; }
.check-group h4::after, .sec > h4::after { content: ''; flex-grow: 1; border-top: var(--rule) solid var(--ink); }
.check { display: grid; grid-template-columns: 22px 1fr; gap: 6px; align-items: start; font-size: 15px; line-height: 1.3; margin: 5px 0; }
.check::before { content: ''; width: 14px; height: 14px; margin-top: 2px; border: var(--rule) solid var(--ink); box-sizing: border-box; }
.warn { background: var(--ink); color: var(--paper); font-weight: 700; text-align: center; text-transform: uppercase; font-size: 15px; line-height: 1.2; padding: 8px; margin-top: 14px; }
.btn { font: inherit; font-weight: 700; font-size: 14px; text-transform: uppercase; letter-spacing: var(--label-tracking); height: 44px; padding: 0 14px; border: var(--border-w) solid var(--ink); background: var(--paper); color: var(--ink); display: inline-flex; align-items: center; justify-content: center; gap: 10px; cursor: pointer; border-radius: 0; }
.btn.primary { background: var(--ink); color: var(--paper); }
.btn svg { width: 14px; height: 14px; fill: currentColor; }
.claude-sessions { position: fixed; right: 12px; bottom: 12px; z-index: 50; display: flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 11px; }
.claude-sessions .cs-label { text-transform: uppercase; letter-spacing: var(--label-tracking); background: var(--paper); padding: 2px 4px; }
.claude-sessions a { color: var(--ink); border: var(--border-w) solid var(--ink); background: var(--paper); padding: 4px 10px; text-decoration: none; }
.claude-sessions a.missing { opacity: .45; pointer-events: none; }
/* this page */
.wrap { max-width: 680px; margin: 0 auto; padding: 16px 16px 72px; box-sizing: border-box; }
.wrap > .card { margin-bottom: 28px; }
.label { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; text-align: center; margin-top: 14px; }
.lede { font-size: 16px; line-height: 1.45; margin: 12px 16px; }
.sec { margin: 18px 16px; }
.sec p { font-size: 16px; line-height: 1.5; margin: 0 0 10px; }
.poem { font-size: 16px; line-height: 1.5; }
.ln { display: grid; grid-template-columns: 30px 1fr; }
.ln .n { font-size: 11px; font-variant-numeric: tabular-nums; text-align: right; padding: 4px 10px 0 0; }
.ln.gap { height: 12px; }
.mk { font-weight: 700; text-decoration: underline; text-decoration-thickness: 2px; text-underline-offset: 3px; }
.dot { display: inline-grid; place-items: center; width: 16px; height: 16px; border-radius: 50%; background: var(--ink); color: var(--paper); font-size: 10px; font-weight: 700; line-height: 1; vertical-align: 0.45em; margin-left: 2px; text-decoration: none; }
.legend { list-style: none; margin: 10px 0 0; padding: 0; }
.legend li { display: grid; grid-template-columns: 24px 1fr; gap: 6px; align-items: start; font-size: 15px; line-height: 1.35; margin: 5px 0; }
.legend .dot { vertical-align: 0; margin: 1px 0 0; }
details { margin-top: 10px; }
summary { font-size: 12px; font-weight: 700; text-transform: uppercase; min-height: 44px; display: flex; align-items: center; gap: 8px; cursor: pointer; list-style: none; }
summary::-webkit-details-marker { display: none; }
summary::after { content: '+'; font-size: 16px; }
details[open] summary::after { content: '\2212'; }
.play { width: 100%; margin-top: 12px; }
.ex { border: var(--rule) solid var(--ink); margin: 10px 0; padding: 10px 12px; }
.ex.fresh { border-style: dashed; }
.ex .cap { font-size: 12px; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
.ex .cap span { font-weight: 400; }
.ex .note { font-size: 15px; line-height: 1.4; margin: 8px 0 0; }
.try { border: 2.5px solid var(--ink); margin: 18px 16px 10px; padding: 10px 12px; }
.try h4 { margin: 0 0 6px; font-size: 15px; font-weight: 700; text-transform: uppercase; }
.try p { margin: 0; font-size: 16px; line-height: 1.45; }
.toc a { color: var(--ink); text-decoration: none; display: block; }
.toc .step p { font-size: 13px; }
.past a { display: flex; align-items: center; min-height: 44px; border-top: var(--rule) solid var(--ink); font-weight: 700; text-transform: uppercase; font-size: 14px; text-decoration: none; }
.past a.this { text-decoration: underline; }
.foot { font-size: 13px; margin: 14px 16px; }
@media (max-width: 480px) { .title { font-size: 34px; } .band { font-size: 17px; } }
@page { size: letter; margin: 0.5in; }
@media print {
  .wrap { max-width: none; padding: 0; }
  .wrap > .card.part { break-before: page; }
  .play, .claude-sessions, .past-card { display: none; }
  summary { display: none; }
}
"""

PLAY_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4v16l13-8z"/></svg>'
STOP_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6h12v12H6z"/></svg>'

JS = """
(function () {
  // Poem, lesson, poem: one player for the page. Each track lists URLs to try in order (this
  // morning's sounds move from audio/ to the archive at the next run).
  var audio = new Audio(), list = null, btn = null, t = 0, s = 0;
  var PLAY = %(play)s, STOP = %(stop)s, NAMES = ['Poem', 'Lesson', 'Poem again'];
  function label(b, playing) {
    b.innerHTML = (playing ? STOP : PLAY) + '<span>' + (playing ? 'Stop &middot; ' + NAMES[t] : b.getAttribute('data-label')) + '</span>';
  }
  function stop() { audio.pause(); audio.removeAttribute('src'); if (btn) label(btn, false); btn = null; list = null; }
  function load() {
    if (!list || t >= list.length) { stop(); return; }
    if (s >= list[t].length) { t++; s = 0; load(); return; }
    audio.src = list[t][s]; audio.play().catch(function () {}); label(btn, true);
  }
  audio.addEventListener('ended', function () { t++; s = 0; load(); });
  audio.addEventListener('error', function () { if (list) { s++; load(); } });
  document.querySelectorAll('.play').forEach(function (b) {
    b.addEventListener('click', function () {
      if (btn === b) { stop(); return; }
      if (btn) stop();
      btn = b; list = JSON.parse(b.getAttribute('data-tracks')); t = 0; s = 0; load();
    });
  });
  window.addEventListener('beforeprint', function () { document.querySelectorAll('details').forEach(function (d) { d.open = true; }); });
  // Claude session links: desktop Macs try the app first, then the web.
  var isMac = /Mac/.test(navigator.platform) && !('ontouchstart' in window);
  document.querySelectorAll('.claude-sessions a').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var href = a.href;
      if (!isMac || href.indexOf('https://claude.ai') !== 0) return;
      e.preventDefault();
      var tm = setTimeout(function () { window.location.href = href; }, 800);
      window.addEventListener('blur', function () { clearTimeout(tm); }, { once: true });
      window.location.href = 'claude://' + href.replace(/^https:\\/\\//, '');
    });
  });
})();
""" % {'play': json.dumps(PLAY_SVG), 'stop': json.dumps(STOP_SVG)}


def esc(s):
    return html.escape(str(s or ''), quote=True)


def prose(s):
    """Escape, then show [[poem words]] in bold."""
    return re.sub(r'\[\[(.+?)\]\]', r'<b>\1</b>', esc(s))


def marked(line, marks):
    """One poem line with its marked words in bold, underlined, numbered."""
    spans = []
    for n, words in marks:
        i = line.find(words)
        if i >= 0 and all(i >= b or i + len(words) <= a for a, b, _ in spans):
            spans.append((i, i + len(words), n))
    out, pos = [], 0
    for a, b, n in sorted(spans):
        out.append(esc(line[pos:a]))
        out.append(f'<span class="mk">{esc(line[a:b])}</span><span class="dot">{n}</span>')
        pos = b
    out.append(esc(line[pos:]))
    return ''.join(out)


def poem_block(lines, a=None, b=None, marks=None):
    """Lines a to b of a poem, by verse-line number (stanza breaks don't count), marks drawn in."""
    V = verse(lines)
    if not V:
        return ''
    a, b = a or 1, b or len(V)
    rows, n = [], a - 1
    for i in range(V[a - 1], V[b - 1] + 1):
        t = lines[i]
        if not t.strip():
            rows.append('<div class="ln gap"></div>')
            continue
        n += 1
        here = [(m['n'], m['words']) for m in (marks or []) if m['line'] == n]
        rows.append(f'<div class="ln"><span class="n">{n}</span><span>{marked(t, here) if here else esc(t)}</span></div>')
    return '<div class="poem">' + '\n'.join(rows) + '</div>'


def day_label(d):
    return f'{d:%A} {d:%b} {d.day}'


def week_label(first, last):
    if first.month == last.month:
        return f'{first:%b} {first.day} to {last.day}, {last.year}'
    return f'{first:%b} {first.day} to {last:%b} {last.day}, {last.year}'


def tracks(day):
    """[[urls for the poem once], [the lesson], [the poem again]] for one morning, or None."""
    f = day['files']
    names = ['poem-first.mp3', 'poem-preface.mp3', 'poem-again.mp3']
    if not all(f.get(n) for n in names):
        return None
    return [[b + n for b in day['bases']] for n in names]


def render(data, days_by_date, anthology, editions, end):
    poems = {p['id']: p for p in anthology}
    parts = data['parts']
    first = datetime.date.fromisoformat(parts[0]['morning'])
    last = datetime.date.fromisoformat(parts[-1]['morning'])
    n = len(parts)
    toc = '\n'.join(
        f'<a href="#part-{i + 1}"><div class="step"><b>{i + 1}</b><div><h4>{esc(p["technique"])}</h4>'
        f'<p>{esc(day_label(datetime.date.fromisoformat(p["morning"])))}</p></div></div></a>'
        for i, p in enumerate(parts))
    cover = f"""<section class="card cover">
  <div class="title">Poetry<br>Workshop</div>
  <div class="band">{esc(week_label(first, last))}</div>
  <p class="lede">{prose(data.get('intro'))}</p>
  <div class="sec toc"><h4>{'Seven' if n == 7 else n} tools, one per morning</h4>
{toc}
  </div>
  <div class="try"><h4>This week's big prompt</h4><p>{prose(data.get('week_prompt'))}</p></div>
  <div class="warn">One part per sitting.<br>Pen in hand.</div>
</section>"""
    blocks = [cover]
    for i, p in enumerate(parts):
        day = datetime.date.fromisoformat(p['morning'])
        src = days_by_date.get(day)
        lines = (src or {}).get('poem', '').split('\n')
        a, b = p['excerpt']
        marks = [dict(m, n=k + 1) for k, m in enumerate(p['marks'])]
        legend = ''.join(f'<li><span class="dot">{m["n"]}</span><span>{prose(m["note"])}</span></li>' for m in marks)
        tr = tracks(src) if src else None
        play = (f'<button class="btn primary play" data-label="Hear it: poem, lesson, poem" data-tracks="{esc(json.dumps(tr))}">'
                f'{PLAY_SVG}<span>Hear it: poem, lesson, poem</span></button>') if tr else ''
        exs = []
        for e in p['examples']:
            q = poems.get(e['poem'])
            if not q:
                continue
            exs.append(f'<div class="ex"><div class="cap">{esc(q["poet"])} <span>&middot; {esc(q["title"])}, {q["year"]}</span></div>'
                       f'{poem_block(q["lines"], e["lines"][0], e["lines"][1])}'
                       f'<p class="note">{prose(e["note"])}</p></div>')
        if p['fresh']['lines']:
            exs.append('<div class="ex fresh"><div class="cap">Written for this lesson</div>'
                       + '<div class="poem">' + ''.join(f'<div class="ln"><span class="n"></span><span>{esc(t)}</span></div>' if t.strip() else '<div class="ln gap"></div>' for t in p['fresh']['lines']) + '</div>'
                       + f'<p class="note">{prose(p["fresh"]["note"])}</p></div>')
        steps = ''.join(f'<div class="step"><b>{k + 1}</b><div><h4>{esc(s["head"])}</h4><p>{prose(s["detail"])}</p></div></div>'
                        for k, s in enumerate(p['steps']))
        checks = ''.join(f'<div class="check">{prose(c)}</div>' for c in p['checklist'])
        blocks.append(f"""<section class="card part" id="part-{i + 1}">
  <div class="label">Part {i + 1} of {n}</div>
  <div class="title">{esc(p['technique'])}</div>
  <div class="band">{esc(day_label(day))}</div>
  <div class="subhead">{prose(p['definition'])}</div>
  <div class="sec"><h4>The morning's lines</h4>
{poem_block(lines, a, b, marks)}
    <ol class="legend">{legend}</ol>
    <details><summary>The whole poem</summary>{poem_block(lines)}</details>
    {play}
  </div>
  <div class="sec"><h4>Go deeper</h4>
    {''.join(f'<p>{prose(t)}</p>' for t in p['deeper'])}
  </div>
  <div class="sec"><h4>Further examples</h4>
    {''.join(exs)}
  </div>
  <div class="sec"><h4>How to use it</h4></div>
  {steps}
  <div class="try"><h4>Try it, 15 minutes</h4><p>{prose(p['exercise'])}</p></div>
  <div class="check-group"><h4>Check your draft</h4>{checks}</div>
  <div class="warn">{esc(p['keep'])}</div>
</section>""")
    past = ''.join('<a href="%s.html"%s>%s</a>' % (e, ' class="this"' if e == end else '', esc(lbl)) for e, lbl in editions)
    blocks.append(f"""<section class="card past-card">
  <div class="band">Past weeks</div>
  <div class="sec past">{past}</div>
  <p class="foot">Built every Sunday from the lessons in the <a href="{BRIEF_URL}">daily brief</a>. The other poems quoted here are in the public domain.</p>
</section>""")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Poetry Workshop</title>
<meta name="description" content="Ben's weekly poetry workshop, {esc(week_label(first, last))}">
<style>{CSS}</style>
</head>
<body>
<main class="wrap">
{chr(10).join(blocks)}
</main>
<div class="claude-sessions">
  <span class="cs-label">claude</span>
  <a href="{SESSION_URL}">code</a>
  <a class="missing" href="#" title="cowork project link pending">cowork</a>
</div>
<script>{JS}</script>
</body>
</html>
"""


# ---------------------------------------------------------------- site, deploy, schedule

def load_anthology():
    try:
        with open(ANTHOLOGY, encoding='utf-8') as f:
            return json.load(f).get('poems', [])
    except (OSError, ValueError):
        return []


def saved():
    """[(end date string, data)] for every saved week, newest first."""
    out = []
    if os.path.isdir(DATA):
        for f in sorted(os.listdir(DATA), reverse=True):
            if re.fullmatch(r'\d{4}-\d{2}-\d{2}\.json', f):
                with open(os.path.join(DATA, f), encoding='utf-8') as fh:
                    out.append((f[:-5], json.load(fh)))
    return out


def render_all():
    anthology = load_anthology()
    weeks = saved()
    os.makedirs(os.path.join(SITE, 'weeks'), exist_ok=True)
    editions = []
    for end, data in weeks:
        a = datetime.date.fromisoformat(data['parts'][0]['morning'])
        b = datetime.date.fromisoformat(data['parts'][-1]['morning'])
        editions.append((end, week_label(a, b)))
    for k, (end, data) in enumerate(weeks):
        days = {d['date']: d for d in week(datetime.date.fromisoformat(end))}
        page = render(data, days, anthology, editions, end)
        with open(os.path.join(SITE, 'weeks', end + '.html'), 'w', encoding='utf-8') as f:
            f.write(page)
        if k == 0:
            idx = page.replace('href="' + end + '.html"', 'href="weeks/' + end + '.html"')
            idx = re.sub(r'href="(\d{4}-\d{2}-\d{2})\.html"', r'href="weeks/\1.html"', idx)
            with open(os.path.join(SITE, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(idx)
    return len(weeks)


def deploy():
    r = subprocess.run(['/bin/bash', DEPLOY], capture_output=True, text=True)
    sys.stdout.write(r.stdout[-2000:])
    if r.returncode:
        sys.stderr.write(r.stderr[-2000:])
        raise SystemExit(f'poem_roundup: deploy failed ({r.returncode})')


def build(end, no_deploy=False):
    days = week(end)
    if len(days) < 3:
        raise SystemExit(f'poem_roundup: only {len(days)} mornings found for the week ending {end}')
    anthology = load_anthology()
    last = next((d for e, d in saved() if e < end.isoformat()), None)
    user = build_prompt(days, anthology, last)
    for attempt in (1, 2):
        text, stop, usage = ask(SYSTEM, user)
        try:
            raw = parse(text)
            break
        except ValueError:
            if attempt == 2:
                raise SystemExit(f'poem_roundup: no JSON back (stop={stop})')
            user += '\n\nYour last reply was not one valid JSON object. Reply with the JSON object only.'
    data = check(raw, days, anthology)
    data.update(end=end.isoformat(), model=MODEL, built=datetime.datetime.now().isoformat(timespec='minutes'),
                usage=usage)
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, end.isoformat() + '.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    render_all()
    print(f'poem_roundup: week ending {end}, {len(data["parts"])} parts, '
          f'{sum(len(p["examples"]) for p in data["parts"])} anthology examples, usage {usage}')
    if not no_deploy:
        deploy()


def due(today):
    """(end date) if a week is due: the Sunday-to-Saturday week before today, once nothing saved overlaps it."""
    back = (today.weekday() - 5) % 7 or 7          # the last Saturday before today
    end = today - datetime.timedelta(days=back)
    weeks = saved()
    if weeks and datetime.date.fromisoformat(weeks[0][0]) > end - datetime.timedelta(days=7):
        return None
    return end


def if_due():
    today = datetime.date.today()
    end = due(today)
    if not end:
        return
    st = ''
    try:
        with open(STATE) as f:
            st = f.read().split()
    except OSError:
        st = []
    n = int(st[2]) if len(st) >= 3 and st[0] == today.isoformat() and st[1] == 'fail' else 0
    if n >= 3:
        return
    try:
        os.mkdir(LOCK)
    except FileExistsError:
        if datetime.datetime.now().timestamp() - os.path.getmtime(LOCK) < 3600:
            return
    try:
        print(f'===== {datetime.datetime.now():%F %T} poem_roundup: week ending {end} =====', flush=True)
        build(end)
        with open(STATE, 'w') as f:
            f.write(f'{today} done {end}\n')
    except BaseException as e:  # noqa: BLE001  (record the failure, retry on a later tick)
        with open(STATE, 'w') as f:
            f.write(f'{today} fail {n + 1}\n')
        print(f'poem_roundup: failed ({e})', flush=True)
    finally:
        os.rmdir(LOCK)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--end')
    ap.add_argument('--if-due', action='store_true')
    ap.add_argument('--render', action='store_true')
    ap.add_argument('--collect', action='store_true')
    ap.add_argument('--no-deploy', action='store_true')
    a = ap.parse_args()
    if a.if_due:
        return if_due()
    if a.render:
        print(f'poem_roundup: rendered {render_all()} weeks')
        if not a.no_deploy:
            deploy()
        return
    end = datetime.date.fromisoformat(a.end) if a.end else datetime.date.today()
    if a.collect:
        for d in week(end):
            print(d['date'], key_of(d['technique']), '|', d['poem'].split('\n')[0][:50], '|', d['lesson'][:90])
        return
    build(end, a.no_deploy)


def key_of(technique):
    t = technique.strip().lower()
    for i, full in enumerate(TECHNIQUES):
        if t == full.lower():
            return KEYS[i]
    return ''


if __name__ == '__main__':
    main()
