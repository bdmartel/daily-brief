#!/usr/bin/env python3
"""recent_mornings.py: the "Last five mornings" card on the brief page (2026-10-15).

Ben, 2026-10-15: "keep the last 5 online instead of one (the audio bits)". Every morning's audio has
always been archived (archive/<date>-audio/, on GitHub Pages), but the page only linked today's. This
card lists this morning plus the four before it, each with the 6 AM wake-up as it played (the Echo
mix), the lesson, the poem and the sound. The buttons hand the tracks to the page's wake-up player.
Ben, 2026-10-15, on the lesson: "give an option where it's POEM, LESSON, POEM as a way to digest it".
So each morning also gets "poem · lesson · poem": the first reading alone, the lesson, then the second
reading with "So — up!" (poem-first.mp3 / poem-again.mp3, cut by the morning script or poem_split.py).

  recent_mornings.py --repo ~/projects/daily-brief --today 2026-10-15 [--count 5] [--print]

Replaces the <!--LAST_FIVE_MORNINGS--> marker in index.html, or a card already there (run after the
day's audio exists, so only files that are really there get a button). --print shows the card instead.

Dates: archive folders are named for the day they were archived, which is the morning AFTER that audio
played (daily-dashboard.sh reads the old title with `grep -P`, which macOS grep lacks, and falls back
to today's date). So a folder's morning is read from its archived page instead: the title carries the
day the brief summarized, and it played the next morning.
"""
import argparse, datetime, html, json, os, re

MARK = '<!--LAST_FIVE_MORNINGS-->'
BEGIN, END = '<!--last-five-mornings-->', '<!--/last-five-mornings-->'
PARTS = [('poem-preface.mp3', 'About the poem', 'lesson'), ('poem.mp3', 'Poem', 'poem'),
         ('wakeup-bed.mp3', 'Sound', 'sound')]
DIGEST = [('poem-first.mp3', 'Poem'), ('poem-preface.mp3', 'About the poem'), ('poem-again.mp3', 'Poem, again')]


def caption(audio_dir):
    try:
        with open(os.path.join(audio_dir, 'bed.txt'), encoding='utf-8') as f:
            fields = f.readline().strip().split('|')
        return fields[1] if len(fields) > 1 else ''
    except OSError:
        return ''


def morning_of(repo, name):
    """The morning an archive folder's audio played: its page title's date + 1 day."""
    try:
        with open(os.path.join(repo, 'archive', name + '.html'), encoding='utf-8') as f:
            m = re.search(r'<title>Daily Brief - ([A-Za-z]+ \d{1,2}, \d{4})</title>', f.read(4096))
        if m:
            return datetime.datetime.strptime(m.group(1), '%B %d, %Y').date() + datetime.timedelta(days=1)
    except (OSError, ValueError):
        pass
    return datetime.date.fromisoformat(name) - datetime.timedelta(days=1)


def mornings(repo, today, count):
    """[(date, url prefix, folder on disk)], newest first: this morning, then the archived ones."""
    out = [(today, 'audio/', os.path.join(repo, 'audio'))]
    names = sorted((d[:-6] for d in os.listdir(os.path.join(repo, 'archive'))
                    if re.fullmatch(r'\d{4}-\d{2}-\d{2}-audio', d)), reverse=True)
    seen = {today}
    for name in names:
        if len(out) >= count:
            break
        day = morning_of(repo, name)
        if day in seen or day > today:
            continue
        seen.add(day)
        out.append((day, f'archive/{name}-audio/', os.path.join(repo, 'archive', name + '-audio')))
    return out


def label(day, today):
    return 'This morning' if day == today else f'{day:%a}, {day:%b} {day.day}'


def build(repo, today, count):
    rows, data = [], []
    for i, (day, prefix, folder) in enumerate(mornings(repo, today, count)):
        short = f'{day:%b} {day.day}'
        wake = [{'src': prefix + 'wakeup-echo.mp3', 'name': f'{short} · the 6 AM wake-up'}] \
            if os.path.exists(os.path.join(folder, 'wakeup-echo.mp3')) else []
        cap = caption(folder)
        parts = [{'src': prefix + f, 'name': f'{short} · ' + (f'Sound: {cap}' if f == 'wakeup-bed.mp3' and cap else n)}
                 for f, n, _ in PARTS if os.path.exists(os.path.join(folder, f))]
        digest = [{'src': prefix + f, 'name': f'{short} · {n}'} for f, n in DIGEST] \
            if all(os.path.exists(os.path.join(folder, f)) for f, _ in DIGEST) else []
        if not wake and not parts:
            continue
        data.append({'wake': wake, 'digest': digest, 'parts': parts})
        k = len(data) - 1
        btn = '<button class="morning-play" data-day="{k}" data-list="{lst}" data-track="{t}">{txt}</button>'
        btns = [btn.format(k=k, lst='wake', t=0, txt='&#9654; 6 AM wake-up')] if wake else []
        btns += [btn.format(k=k, lst='digest', t=0, txt='&#9654; poem · lesson · poem')] if digest else []
        btns += [btn.format(k=k, lst='parts', t=j, txt=next(s for f, _, s in PARTS if p['src'].endswith(f)))
                 for j, p in enumerate(parts)]
        rows.append(
            '    <div style="display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 12px;padding:9px 0;'
            + ('border-top:1px solid rgba(216,178,90,0.15);' if rows else '') + '">\n'
            f'      <span style="font-size:13px;color:var(--text,#e8e6e1);min-width:96px;">{html.escape(label(day, today))}</span>\n'
            f'      <span style="flex:1 1 220px;font-family:Georgia,\'Times New Roman\',serif;font-size:14px;color:var(--text-muted,#9a948a);">{html.escape(cap)}</span>\n'
            f'      <span style="display:flex;flex-wrap:wrap;gap:6px;">{" ".join(btns)}</span>\n'
            '    </div>')
    if not rows:
        return ''
    js = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return (f'  {BEGIN}\n'
            '  <div class="mornings-card" style="margin:0 0 24px;padding:16px 24px 10px;border-left:3px solid #d8b25a;'
            'background:rgba(216,178,90,0.05);border-radius:10px;">\n'
            '    <style>.mornings-card .morning-play{background:none;border:1px solid #d8b25a;color:#d8b25a;border-radius:14px;'
            'padding:3px 11px;font-size:11px;cursor:pointer;letter-spacing:0.04em;}</style>\n'
            '    <div style="font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:var(--text-muted,#9a948a);'
            f'margin-bottom:4px;">Last {len(rows)} mornings</div>\n'
            + '\n'.join(rows) + '\n'
            f'    <script>var pastMornings = {js};</script>\n'
            f'  </div>\n  {END}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument('--today', default=datetime.date.today().isoformat())
    ap.add_argument('--count', type=int, default=5)
    ap.add_argument('--print', action='store_true')
    a = ap.parse_args()
    card = build(a.repo, datetime.date.fromisoformat(a.today), a.count)
    if a.print:
        print(card)
        return
    page = os.path.join(a.repo, 'index.html')
    with open(page, encoding='utf-8') as f:
        s = f.read()
    i, j = s.find(BEGIN), s.find(END)
    if MARK in s:
        s = s.replace(MARK, card.strip(), 1)
    elif 0 <= i < j:                       # a card already there (a re-run): replace it
        s = s[:i] + card.strip() + s[j + len(END):]
    else:
        return
    with open(page, 'w', encoding='utf-8') as f:
        f.write(s)


if __name__ == '__main__':
    main()
