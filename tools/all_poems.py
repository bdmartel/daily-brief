#!/usr/bin/env python3
"""all_poems.py: the "All the poems" accordion on the brief page (2026-11-08).

Ben, 2026-11-08: "i'd like to be able to read all of the poems on the daily brief in an accordion".
Every morning's poem is already in its archived page (the poem-card). This gathers them, newest first,
one per morning (the last take of a morning wins; draft pages like -v2 count only if the morning has
no plain page), and puts a collapsible list under the Last-5 card: one row per morning, tap to open.

  all_poems.py --repo ~/projects/daily-brief [--print]

Dates: an archived page's title carries the day it summarized; its poem played the next morning
(same rule as recent_mornings.py). index.html is this morning. Re-runs replace the block between the
<!--all-poems--> comments. The block is also stripped from archive pages so they don't each carry
the whole collection.
"""
import argparse, datetime, glob, html, os, re

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


def gather(repo):
    """{morning: poem html}, plain archive pages beat -vN drafts; index.html is newest."""
    found = {}
    files = sorted(glob.glob(os.path.join(repo, 'archive', '*.html')))
    plain = [f for f in files if re.fullmatch(r'\d{4}-\d{2}-\d{2}\.html', os.path.basename(f))]
    drafts = [f for f in files if f not in plain]
    for f in drafts + plain + [os.path.join(repo, 'index.html')]:   # later sources overwrite
        day, text = read_poem(f)
        if day:
            found[day] = text
    return found


def first_line(text):
    line = html.unescape(re.sub(r'<[^>]+>', '', text)).strip().split('\n')[0].strip()
    return line if len(line) <= 70 else line[:67].rstrip(' ,;:—-') + '…'


def build(repo):
    poems = gather(repo)
    if not poems:
        return ''
    rows = []
    for day in sorted(poems, reverse=True):
        rows.append(
            '    <details class="poem-fold">\n'
            f'      <summary><span class="pf-date">{day:%a}, {day:%b} {day.day}, {day.year}</span>'
            f'<span class="pf-first">{html.escape(first_line(poems[day]))}</span></summary>\n'
            f'      <div class="pf-text">{poems[day]}</div>\n'
            '    </details>')
    return (f'  {BEGIN}\n'
            '  <div class="all-poems-card" style="margin:0 0 24px;padding:16px 24px 10px;border-left:3px solid #d8b25a;'
            'background:rgba(216,178,90,0.05);border-radius:10px;">\n'
            '    <style>'
            '.all-poems-card details.poem-fold{border-top:1px solid rgba(216,178,90,0.15);}'
            '.all-poems-card summary{list-style:none;cursor:pointer;display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 12px;padding:10px 0;}'
            '.all-poems-card summary::-webkit-details-marker{display:none;}'
            '.all-poems-card summary::before{content:"+";color:#d8b25a;width:12px;font-size:14px;}'
            '.all-poems-card details[open] summary::before{content:"\\2212";}'
            '.all-poems-card .pf-date{font-size:13px;color:var(--text,#e8e6e1);min-width:130px;}'
            '.all-poems-card .pf-first{flex:1 1 220px;font-family:Georgia,\'Times New Roman\',serif;font-size:14px;font-style:italic;color:var(--text-muted,#9a948a);}'
            '.all-poems-card .pf-text{font-family:Georgia,\'Times New Roman\',serif;font-size:16px;line-height:1.75;color:var(--text,#e8e6e1);white-space:pre-line;padding:2px 0 16px 24px;}'
            '.all-poems-card .pf-tools{display:flex;gap:8px;}'
            '.all-poems-card .pf-tools button{background:none;border:1px solid #d8b25a;color:#d8b25a;border-radius:14px;padding:3px 11px;font-size:11px;cursor:pointer;letter-spacing:0.04em;}'
            '</style>\n'
            '    <div style="display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 12px;font-size:11px;letter-spacing:0.14em;'
            'text-transform:uppercase;color:var(--text-muted,#9a948a);margin-bottom:6px;">'
            f'<span>All the poems ({len(rows)})</span>'
            '<span class="pf-tools" style="margin-left:auto;">'
            '<button type="button" onclick="this.closest(\'.all-poems-card\').querySelectorAll(\'details\').forEach(function(d){d.open=true})">open all</button>'
            '<button type="button" onclick="this.closest(\'.all-poems-card\').querySelectorAll(\'details\').forEach(function(d){d.open=false})">close all</button>'
            '</span></div>\n'
            + '\n'.join(rows) + '\n'
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
