#!/usr/bin/env python3
"""all_poems.py: the "All the poems" card on the brief page (2026-11-08, grown 2026-11-17).

Ben, 2026-11-08: "i'd like to be able to read all of the poems on the daily brief in an accordion".
Ben, 2026-11-17: "Make it so I can autoplay all. Also make it so I can click through to lesson of that
one. Also make it so all lessons are more accessible".

The card has two views:
  Poems    one row per morning, newest first; tap to open the poem. Inside: play the poem, play its
           lesson, or lesson-then-poem, and "Read the lesson" opens that morning's lesson text.
  Lessons  every morning that had a lesson, with its technique, the text and a play button, and a link
           back to that morning's poem.
"Play all" walks every morning in order (poems only, or lesson + poem), opening and highlighting the
one that is playing; it continues from a row if you start it there.

  all_poems.py --repo ~/projects/daily-brief [--print]

Sources: poem text from each archived page's poem-card (plain pages beat -vN drafts); audio and the
lesson from the matching audio folder (archive/<name>-audio/, or audio/ for this morning). Lesson text
is audio/lesson.json (written by the morning script since Oct 16; older ones were transcribed from
poem-preface.mp3). Audio paths are written relative ('archive/…-audio/…', 'audio/…'); tools/sounds.py,
which runs after this, re-points them at Cloudflare.

Dates: an archived page's title carries the day it summarized; its poem played the next morning
(same rule as recent_mornings.py). Re-runs replace the block between the <!--all-poems--> comments,
and the block is stripped from archive pages so they don't each carry the whole collection.
"""
import argparse, datetime, glob, html, json, os, re

BEGIN, END = '<!--all-poems-->', '<!--/all-poems-->'
ANCHOR = '<!--/last-five-mornings-->'
POEM = re.compile(r'<div style="font-family:Georgia[^"]*white-space:pre-line;">(.*?)</div>', re.S)
TITLE = re.compile(r'<title>Daily Brief - ([A-Za-z]+ \d{1,2}, \d{4})</title>')


def read_poem(path):
    try:
        with open(path, encoding='utf-8') as f:
            s = f.read()
    except OSError:
        return None, None
    t = TITLE.search(s[:4096])
    i = s.find('class="poem-card"')
    if not t or i < 0:
        return None, None
    m = POEM.search(s, i, i + 8000)
    if not m:
        return None, None
    try:
        day = datetime.datetime.strptime(t.group(1), '%B %d, %Y').date() + datetime.timedelta(days=1)
    except ValueError:
        return None, None
    text = m.group(1).strip()
    return (day, text) if text else (None, None)


def audio_for(repo, page):
    """(url prefix, local folder) of a page's audio, or (None, None)."""
    if os.path.basename(page) == 'index.html':
        return 'audio/', os.path.join(repo, 'audio')
    name = os.path.basename(page)[:-5]
    folder = os.path.join(repo, 'archive', name + '-audio')
    return (f'archive/{name}-audio/', folder) if os.path.isdir(folder) else (None, None)


def lesson_of(folder):
    try:
        with open(os.path.join(folder, 'lesson.json'), encoding='utf-8') as f:
            j = json.load(f)
        return (j.get('technique') or '').strip(), (j.get('lesson') or '').strip(), j.get('lesson_source', '')
    except (OSError, ValueError):
        return '', '', ''


def gather(repo):
    """{morning: {...}}; plain archive pages beat -vN drafts; index.html is newest."""
    found = {}
    files = sorted(glob.glob(os.path.join(repo, 'archive', '*.html')))
    plain = [f for f in files if re.fullmatch(r'\d{4}-\d{2}-\d{2}\.html', os.path.basename(f))]
    drafts = [f for f in files if f not in plain]
    for f in drafts + plain + [os.path.join(repo, 'index.html')]:   # later sources overwrite
        day, text = read_poem(f)
        if not day:
            continue
        rec = {'text': text, 'poem': '', 'lesson': '', 'technique': '', 'lesson_text': '', 'source': ''}
        prefix, folder = audio_for(repo, f)
        if prefix:
            for name in ('poem-first.mp3', 'poem.mp3'):          # one reading when it exists
                if os.path.exists(os.path.join(folder, name)):
                    rec['poem'] = prefix + name
                    break
            if os.path.exists(os.path.join(folder, 'poem-preface.mp3')):
                rec['lesson'] = prefix + 'poem-preface.mp3'
            rec['technique'], rec['lesson_text'], rec['source'] = lesson_of(folder)
        found[day] = rec
    return found


def first_line(text):
    line = html.unescape(re.sub(r'<[^>]+>', '', text)).strip().split('\n')[0].strip()
    return line if len(line) <= 70 else line[:67].rstrip(' ,;:—-') + '…'


def short_technique(t):
    t = t.split(' — ')[0].split(' - ')[0].strip()
    return t[:1].upper() + t[1:] if t else ''


CSS = (
    '.all-poems-card details.poem-fold,.all-poems-card details.lesson-fold{border-top:1px solid rgba(216,178,90,0.15);}'
    '.all-poems-card summary{list-style:none;cursor:pointer;display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 12px;padding:10px 0;}'
    '.all-poems-card summary::-webkit-details-marker{display:none;}'
    '.all-poems-card summary::before{content:"+";color:#d8b25a;width:12px;font-size:14px;}'
    '.all-poems-card details[open]>summary::before{content:"\\2212";}'
    '.all-poems-card .pf-date{font-size:13px;color:var(--text,#e8e6e1);min-width:130px;}'
    '.all-poems-card .pf-first{flex:1 1 220px;font-family:Georgia,\'Times New Roman\',serif;font-size:14px;font-style:italic;color:var(--text-muted,#9a948a);}'
    '.all-poems-card .pf-tech{font-size:11px;letter-spacing:0.04em;color:#d8b25a;}'
    '.all-poems-card .pf-text{font-family:Georgia,\'Times New Roman\',serif;font-size:16px;line-height:1.75;color:var(--text,#e8e6e1);white-space:pre-line;padding:2px 0 12px 24px;}'
    '.all-poems-card .pf-lesson{font-size:15px;line-height:1.7;color:var(--text,#e8e6e1);padding:4px 0 12px 24px;}'
    '.all-poems-card .pf-lesson .pf-note{font-size:11px;color:var(--text-muted,#9a948a);}'
    '.all-poems-card .pf-row{display:flex;flex-wrap:wrap;gap:6px;padding:0 0 12px 24px;}'
    '.all-poems-card button.pf-b{background:none;border:1px solid #d8b25a;color:#d8b25a;border-radius:14px;padding:3px 11px;font-size:11px;cursor:pointer;letter-spacing:0.04em;}'
    '.all-poems-card button.pf-b.on{background:#d8b25a;color:#1a1814;}'
    '.all-poems-card .pf-tabs button{background:none;border:none;color:var(--text-muted,#9a948a);font-size:11px;letter-spacing:0.14em;text-transform:uppercase;cursor:pointer;padding:2px 0;margin-right:14px;border-bottom:2px solid transparent;}'
    '.all-poems-card .pf-tabs button.on{color:var(--text,#e8e6e1);border-bottom-color:#d8b25a;}'
    '.all-poems-card details.playing>summary .pf-date{color:#d8b25a;}'
    '.all-poems-card details.playing{background:rgba(216,178,90,0.07);}'
    '.all-poems-card .pf-bar{display:none;align-items:center;gap:8px;flex-wrap:wrap;padding:8px 10px;margin:4px 0 8px;border-radius:8px;background:rgba(216,178,90,0.1);font-size:12px;color:var(--text,#e8e6e1);}'
    '.all-poems-card .pf-bar.on{display:flex;}'
    '.all-poems-card .pf-view[hidden]{display:none;}'
    '.all-poems-card label.pf-opt{font-size:11px;color:var(--text-muted,#9a948a);display:flex;align-items:center;gap:4px;letter-spacing:0.04em;}'
)

JS = r'''
(function(){
  var card = document.currentScript.closest('.all-poems-card');
  var rows = Array.prototype.slice.call(card.querySelectorAll('details.poem-fold'));
  var audio = new Audio(), queue = [], qi = -1, bar = card.querySelector('.pf-bar'), now = card.querySelector('.pf-now');
  function q(sel){ return card.querySelector(sel); }
  function label(r, kind){ return r.dataset.label + ' · ' + (kind === 'lesson' ? 'lesson' : 'poem'); }
  function mark(r){
    rows.forEach(function(x){ x.classList.remove('playing'); });
    if (r) { r.classList.add('playing'); r.open = true; }
  }
  function playAt(i){
    qi = i;
    if (i < 0 || i >= queue.length) { stop(); return; }
    var it = queue[i];
    if (it.scroll !== false) showView('poems');
    mark(it.row);
    if (it.kind === 'lesson') { var ld = it.row.querySelector('details.pf-ldet'); if (ld) ld.open = true; }
    now.textContent = label(it.row, it.kind);
    bar.classList.add('on');
    q('.pf-pause').textContent = 'pause';
    audio.src = it.src;
    audio.play().catch(function(){});
    if (it.scroll !== false) it.row.scrollIntoView({behavior:'smooth', block:'start'});
  }
  function stop(){
    audio.pause(); queue = []; qi = -1; mark(null); bar.classList.remove('on');
  }
  audio.addEventListener('ended', function(){ playAt(qi + 1); });
  audio.addEventListener('error', function(){ if (qi >= 0) playAt(qi + 1); });
  function items(r, mode){
    var out = [];
    if (mode !== 'poem' && r.dataset.lesson) out.push({row:r, kind:'lesson', src:r.dataset.lesson});
    if (mode !== 'lesson' && r.dataset.poem) out.push({row:r, kind:'poem', src:r.dataset.poem});
    return out;
  }
  function playAll(fromRow){
    var withLessons = q('.pf-withl').checked, start = fromRow ? rows.indexOf(fromRow) : 0;
    queue = [];
    rows.slice(start).forEach(function(r){ queue = queue.concat(items(r, withLessons ? 'both' : 'poem')); });
    playAt(0);
  }
  q('.pf-all').addEventListener('click', function(){ playAll(null); });
  q('.pf-pause').addEventListener('click', function(){
    if (audio.paused) { audio.play(); this.textContent = 'pause'; } else { audio.pause(); this.textContent = 'resume'; }
  });
  q('.pf-next').addEventListener('click', function(){ playAt(qi + 1); });
  q('.pf-prev').addEventListener('click', function(){ playAt(Math.max(0, qi - 1)); });
  q('.pf-stop').addEventListener('click', stop);
  card.addEventListener('click', function(e){
    var b = e.target.closest('button[data-act]');
    if (!b) return;
    var r = b.closest('details.poem-fold') || card.querySelector('details.poem-fold[data-day="' + b.dataset.day + '"]');
    var act = b.dataset.act;
    if (act === 'from') { playAll(r); return; }
    if (act === 'see-poem') {
      showView('poems'); r.open = true; r.scrollIntoView({behavior:'smooth', block:'start'}); return;
    }
    if (act === 'see-lesson') {
      var ld = r.querySelector('details.pf-ldet'); if (ld) { ld.open = true; ld.scrollIntoView({behavior:'smooth', block:'nearest'}); } return;
    }
    queue = items(r, act); queue.forEach(function(x){ x.scroll = false; }); playAt(0);
  });
  function showView(v){
    card.querySelectorAll('.pf-view').forEach(function(x){ x.hidden = x.dataset.view !== v; });
    card.querySelectorAll('.pf-tabs button').forEach(function(x){ x.classList.toggle('on', x.dataset.view === v); });
  }
  card.querySelectorAll('.pf-tabs button').forEach(function(b){ b.addEventListener('click', function(){ showView(b.dataset.view); }); });
  q('.pf-openall').addEventListener('click', function(){ card.querySelectorAll('.pf-view:not([hidden]) > details').forEach(function(d){ d.open = true; }); });
  q('.pf-closeall').addEventListener('click', function(){ card.querySelectorAll('.pf-view:not([hidden]) > details').forEach(function(d){ d.open = false; }); });
})();
'''


def build(repo):
    poems = gather(repo)
    if not poems:
        return ''
    days = sorted(poems, reverse=True)
    prows, lrows = [], []
    for day in days:
        r = poems[day]
        iso = day.isoformat()
        lab = f'{day:%a}, {day:%b} {day.day}, {day.year}'
        short = f'{day:%b} {day.day}'
        tech = short_technique(r['technique'])
        btns = []
        if r['poem']:
            btns.append(f'<button class="pf-b" data-act="poem">&#9654; poem</button>')
        if r['lesson']:
            btns.append(f'<button class="pf-b" data-act="lesson">&#9654; lesson</button>')
        if r['poem'] and r['lesson']:
            btns.append(f'<button class="pf-b" data-act="both">&#9654; lesson, then poem</button>')
        if r['poem'] or r['lesson']:
            btns.append(f'<button class="pf-b" data-act="from">&#9654; play all from here</button>')
        lesson_html = ''
        if r['lesson_text'] or r['lesson']:
            note = ('<div class="pf-note">Transcribed from the audio, so a word here or there may be off.</div>'
                    if r['source'] == 'transcribed' else '')
            body = html.escape(r['lesson_text']) if r['lesson_text'] else '<span class="pf-note">This lesson is audio only. Press ▶ lesson to hear it.</span>'
            lesson_html = (
                '      <details class="pf-ldet" style="padding-left:24px;"><summary><span class="pf-tech">'
                f'Read the lesson{": " + html.escape(tech) if tech else ""}</span></summary>\n'
                f'        <div class="pf-lesson" style="padding-left:12px;">{body}{note}</div>\n'
                '      </details>\n')
        attrs = (f' data-day="{iso}" data-label="{html.escape(short)}"'
                 + (f' data-poem="{r["poem"]}"' if r['poem'] else '')
                 + (f' data-lesson="{r["lesson"]}"' if r['lesson'] else ''))
        prows.append(
            f'    <details class="poem-fold"{attrs}>\n'
            f'      <summary><span class="pf-date">{lab}</span>'
            f'<span class="pf-first">{html.escape(first_line(r["text"]))}</span></summary>\n'
            + (f'      <div class="pf-row">{" ".join(btns)}</div>\n' if btns else '')
            + f'      <div class="pf-text">{r["text"]}</div>\n'
            + lesson_html
            + '    </details>')
        if r['lesson_text'] or r['lesson']:
            lb = []
            if r['lesson']:
                lb.append(f'<button class="pf-b" data-act="lesson" data-day="{iso}">&#9654; lesson</button>')
            if r['poem'] and r['lesson']:
                lb.append(f'<button class="pf-b" data-act="both" data-day="{iso}">&#9654; lesson, then poem</button>')
            lb.append(f'<button class="pf-b" data-act="see-poem" data-day="{iso}">see the poem &rarr;</button>')
            body = html.escape(r['lesson_text']) if r['lesson_text'] else '<span class="pf-note">Audio only. Press ▶ lesson to hear it.</span>'
            note = ('<div class="pf-note">Transcribed from the audio, so a word here or there may be off.</div>'
                    if r['source'] == 'transcribed' else '')
            lrows.append(
                '    <details class="lesson-fold">\n'
                f'      <summary><span class="pf-date">{lab}</span>'
                f'<span class="pf-first" style="font-style:normal;">{html.escape(tech) if tech else html.escape(first_line(r["text"]))}</span></summary>\n'
                f'      <div class="pf-row">{" ".join(lb)}</div>\n'
                f'      <div class="pf-lesson">{body}{note}</div>\n'
                '    </details>')
    return (f'  {BEGIN}\n'
            '  <div class="all-poems-card" style="margin:0 0 24px;padding:16px 24px 10px;border-left:3px solid #d8b25a;'
            'background:rgba(216,178,90,0.05);border-radius:10px;">\n'
            f'    <style>{CSS}</style>\n'
            '    <div style="display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;margin-bottom:6px;">'
            '<span class="pf-tabs">'
            f'<button type="button" data-view="poems" class="on">All the poems ({len(prows)})</button>'
            f'<button type="button" data-view="lessons">All the lessons ({len(lrows)})</button></span>'
            '<span style="margin-left:auto;display:flex;flex-wrap:wrap;gap:6px;align-items:center;">'
            '<button type="button" class="pf-b pf-all">&#9654; play all</button>'
            '<label class="pf-opt"><input type="checkbox" class="pf-withl"> with lessons</label>'
            '<button type="button" class="pf-b pf-openall">open all</button>'
            '<button type="button" class="pf-b pf-closeall">close all</button>'
            '</span></div>\n'
            '    <div class="pf-bar"><span>&#9835;</span><span class="pf-now" style="flex:1 1 140px;"></span>'
            '<button type="button" class="pf-b pf-prev">&larr; back</button>'
            '<button type="button" class="pf-b pf-pause">pause</button>'
            '<button type="button" class="pf-b pf-next">next &rarr;</button>'
            '<button type="button" class="pf-b pf-stop">stop</button></div>\n'
            '    <div class="pf-view" data-view="poems">\n' + '\n'.join(prows) + '\n    </div>\n'
            '    <div class="pf-view" data-view="lessons" hidden>\n' + '\n'.join(lrows) + '\n    </div>\n'
            f'    <script>{JS}</script>\n'
            f'  </div>\n  {END}')


def strip_block(s):
    i, j = s.find(BEGIN), s.find(END)
    if 0 <= i < j:
        return s[:i].rstrip(' ') + s[j + len(END):].lstrip('\n')
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument('--print', action='store_true')
    a = ap.parse_args()
    for f in glob.glob(os.path.join(a.repo, 'archive', '*.html')):   # keep archived pages light
        with open(f, encoding='utf-8') as fh:
            s = fh.read()
        if BEGIN in s:
            with open(f, 'w', encoding='utf-8') as fh:
                fh.write(strip_block(s))
    block = build(a.repo)
    if a.print:
        print(block)
        return
    page = os.path.join(a.repo, 'index.html')
    with open(page, encoding='utf-8') as f:
        s = f.read()
    s = strip_block(s)
    if not block:
        pass
    elif ANCHOR in s:
        k = s.find(ANCHOR) + len(ANCHOR)
        s = s[:k] + '\n' + block + s[k:]
    else:                                  # no Last-5 card: go right after the poem card
        i = s.find('class="poem-card"')
        m = re.search(r'</div>\s*</div>', s[i:]) if i >= 0 else None
        if not m:
            return
        k = i + m.end()
        s = s[:k] + '\n' + block + s[k:]
    with open(page, 'w', encoding='utf-8') as f:
        f.write(s)


if __name__ == '__main__':
    main()
