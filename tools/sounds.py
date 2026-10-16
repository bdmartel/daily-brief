#!/usr/bin/env python3
"""sounds.py: the brief's sounds live on Cloudflare, shrunk (2026-10-16).

Ben, 2026-10-15: "store all sounds ... so space is less of a concern"; asked for something free and
public, he picked "Cloudflare + shrink". GitHub Pages was carrying 1.3 GB of audio against its 1 GB
site limit, and the droplet had 1.2 GB free. Now every sound is served from a Cloudflare Worker
(static assets, free: 20,000 files, 25 MB each, no storage or bandwidth bill), and GitHub keeps only
the pages.

  https://brief-sounds.bdmartel.workers.dev/m/<morning>/<file>.mp3   mornings from Oct 16 on
  https://brief-sounds.bdmartel.workers.dev/a/<folder>/<file>.mp3    older archive folders, by name
  https://brief-sounds.bdmartel.workers.dev/latest/<file>.mp3        redirect to the newest morning

Older folders keep their folder name because the morning a folder played can't always be told
(on 7 mornings two folders carry the same page title). From Oct 16 the morning's date is written
into the folder (.published) when it goes up, and the archive copies it along.

Shrinking: mono files are voice (lesson, poem, the voice track) and go to 48 kbps, about a third of
128 kbps, with no audible change in speech; stereo files (the 6 AM wake-up with its field
recording, the sound alone) go to 96 kbps, three quarters. The originals stay on the Mac
(audio/, archive/<name>-audio/), out of git.

  sounds.py publish --today 2026-10-16   shrink what's new into sounds/public, upload, then point
                                          the pages and the Echo feed at it (the morning script)
  sounds.py rewrite [--today ...]        only re-point the pages, for what is already online
  sounds.py url 2026-10-16 poem.mp3

publish exits 1 if the upload fails; the pages are still re-pointed for everything already online,
and today's links stay relative so the morning script can put today's sounds on GitHub instead.
"""
import argparse, concurrent.futures, datetime, glob, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
STAGE = os.path.join(REPO, 'sounds')                 # gitignored: wrangler.jsonc, public/, deploy/
PUBLIC = os.path.join(STAGE, 'public')               # every shrunk file
DEPLOY = os.path.join(STAGE, 'deploy')               # what one upload sends (hard links into public/)
ONLINE = os.path.join(STAGE, 'online.json')          # folders confirmed uploaded
# The Mac uploads at about 0.25 MB/s, and wrangler gives up on an upload request that runs past
# about 5 minutes, so the 777 MB backlog went up in batches: each upload adds at most this much.
BATCH = 24 * 2 ** 20
MORNING_EXTRA = 12 * 2 ** 20                         # backlog riding along with each morning
NAME = 'brief-sounds'
URL = 'https://brief-sounds.bdmartel.workers.dev'
MARK = '.published'
GH_AUDIO = 'https://bdmartel.github.io/daily-brief/audio/'

HEADERS = """/*
  X-Robots-Tag: noindex
/m/*
  Cache-Control: public, max-age=31536000, immutable
/a/*
  Cache-Control: public, max-age=31536000, immutable
"""
INDEX = ('<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex">'
         '<title>Brief sounds</title><p>Sounds for Ben\'s daily brief.</p>')


def rel_for(folder):
    """Where one local audio folder lives online: m/<morning> once it was published, else a/<name>."""
    try:
        with open(os.path.join(folder, MARK)) as f:
            r = f.read().strip()
        if re.fullmatch(r'm/\d{4}-\d{2}-\d{2}', r):
            return r
    except OSError:
        pass
    name = os.path.basename(folder.rstrip('/'))
    return 'a/' + (name[:-len('-audio')] if name.endswith('-audio') else name)


def folders(today=None):
    """[(local folder, online dir)] for today's audio/ and every archive folder."""
    out = []
    if today:
        out.append((os.path.join(REPO, 'audio'), f'm/{today}'))
    for d in sorted(glob.glob(os.path.join(REPO, 'archive', '*-audio'))):
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}-audio', os.path.basename(d)):
            out.append((d, rel_for(d)))
    return out


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries',
                        'stream=channels,bit_rate', '-of', 'json', path], capture_output=True, text=True)
    s = (json.loads(r.stdout or '{}').get('streams') or [{}])[0]
    return int(s.get('channels') or 1), int(s.get('bit_rate') or 0)


def shrink(src, dst):
    """Voice (mono) to 48 kbps, mixes (stereo) to 96 kbps; anything already smaller is copied."""
    ch, br = probe(src)
    target = 96000 if ch >= 2 else 48000
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + '.part'
    if br and br <= target * 1.15:
        shutil.copyfile(src, tmp)
    else:
        r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-map', '0:a:0', '-c:a', 'libmp3lame',
                            '-b:a', str(target), '-f', 'mp3', tmp], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f'ffmpeg failed on {src}: {r.stderr[-300:]}')
    os.replace(tmp, dst)


def sync(today=None):
    """Bring sounds/public up to date: every mp3 that should be online, shrunk once."""
    jobs = []
    for folder, rel in folders(today):
        for f in sorted(glob.glob(os.path.join(folder, '*.mp3'))):
            dst = os.path.join(PUBLIC, rel, os.path.basename(f))
            if not os.path.exists(dst):
                jobs.append((f, dst))
    def one(job):
        try:
            shrink(*job)
        except Exception as e:  # noqa: BLE001  (one bad old file shouldn't stop the morning)
            print(f'sounds: skipped {job[0]}: {e}')
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
        list(ex.map(one, jobs))
    with open(os.path.join(STAGE, 'wrangler.jsonc'), 'w') as f:
        json.dump({'name': NAME, 'main': '../tools/sounds-worker.js', 'compatibility_date': '2026-10-01',
                   'workers_dev': True,
                   'assets': {'directory': './deploy', 'binding': 'ASSETS', 'run_worker_first': True,
                              'not_found_handling': 'none'}}, f, indent=1)
    return len(jobs)


def staged():
    """{online dir: bytes} for every folder in sounds/public."""
    out = {}
    for d in glob.glob(os.path.join(PUBLIC, '[am]', '*')):
        rel = os.path.relpath(d, PUBLIC)
        out[rel] = sum(os.path.getsize(f) for f in glob.glob(os.path.join(d, '*.mp3')))
    return out


def choose(today, extra):
    """What the next upload holds: everything already online, today's morning, and then the
    backlog (newest first) until `extra` bytes of new files."""
    sizes, want = staged(), set(online())
    if today and f'm/{today}' in sizes:
        want.add(f'm/{today}')
    added = 0
    backlog = sorted((r for r in sizes if r not in want), key=lambda r: (r[0] == 'm', r[2:]), reverse=True)
    for rel in backlog:
        if added and added + sizes[rel] > extra:
            break
        want.add(rel)
        added += sizes[rel]
    return want & set(sizes)


def build_deploy(want):
    shutil.rmtree(DEPLOY, ignore_errors=True)
    for rel in sorted(want):
        os.makedirs(os.path.join(DEPLOY, rel))
        for f in glob.glob(os.path.join(PUBLIC, rel, '*.mp3')):
            os.link(f, os.path.join(DEPLOY, rel, os.path.basename(f)))
    with open(os.path.join(DEPLOY, '_headers'), 'w') as f:
        f.write(HEADERS)
    newest = sorted(r for r in want if r.startswith('m/'))
    with open(os.path.join(DEPLOY, '_redirects'), 'w') as f:
        if newest:
            f.write(f'/latest/* /{newest[-1]}/:splat 302\n')
    with open(os.path.join(DEPLOY, 'index.html'), 'w') as f:
        f.write(INDEX)


def wrangler():
    """wrangler lives under nvm, which launchd's PATH doesn't know."""
    found = shutil.which('wrangler')
    if not found:
        cands = sorted(glob.glob(os.path.expanduser('~/.nvm/versions/node/*/bin/wrangler')))
        found = cands[-1] if cands else None
    if not found:
        raise RuntimeError('wrangler not found (npm install -g wrangler)')
    return found


def deploy(want):
    """Upload exactly `want`; on success it becomes the record of what is online."""
    build_deploy(want)
    w = wrangler()
    env = dict(os.environ, CI='true', WRANGLER_SEND_METRICS='false',
               PATH=os.path.dirname(w) + os.pathsep + os.environ.get('PATH', '/usr/bin:/bin'))
    r = subprocess.run([w, 'deploy'], cwd=STAGE, env=env, capture_output=True, text=True, timeout=1800)
    if r.returncode:
        raise RuntimeError(f'wrangler deploy failed: {(r.stderr or r.stdout)[-600:]}')
    with open(ONLINE, 'w') as f:
        json.dump(sorted(want), f, indent=0)


def untrack():
    """Take the mp3s that are online out of git; the copies on disk stay."""
    up, paths = online(), []
    for folder, rel in folders():
        if rel in up:
            paths += glob.glob(os.path.join(folder, '*.mp3'))
    marked = os.path.join(REPO, 'audio', MARK)
    if os.path.exists(marked):
        paths += glob.glob(os.path.join(REPO, 'audio', '*.mp3'))
    tracked = subprocess.run(['git', 'ls-files', '--', *[os.path.relpath(p, REPO) for p in paths]],
                             cwd=REPO, capture_output=True, text=True).stdout.split() if paths else []
    for k in range(0, len(tracked), 200):
        subprocess.run(['git', 'rm', '-q', '--cached', '--', *tracked[k:k + 200]], cwd=REPO, check=True)
    return len(tracked)


def online():
    try:
        with open(ONLINE) as f:
            return set(json.load(f))
    except (OSError, ValueError):
        return set()


def rewrite(today=None):
    """Point the pages, the Echo feed and the phone page at the sounds that are online."""
    up = online()
    changed = []

    def folder_url(name):
        rel = rel_for(os.path.join(REPO, 'archive', name + '-audio'))
        return f'{URL}/{rel}/' if rel in up else None

    def sub_folders(s, pattern):
        return re.sub(pattern, lambda m: m.group(1) + (folder_url(m.group(2)) or m.group(0)[1:]), s)

    def save(path, s, old):
        if s != old:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(s)
            changed.append(os.path.relpath(path, REPO))

    page = os.path.join(REPO, 'index.html')
    if os.path.exists(page):
        old = s = open(page, encoding='utf-8').read()
        if today and f'm/{today}' in up:
            s = re.sub(r'''(['"])audio/(?!(?:mpeg|mp4|ogg|wav|webm|aac|x-)[a-z0-9.+-]*['"])''', lambda m: m.group(1) + f'{URL}/m/{today}/', s)
        s = sub_folders(s, r'''(['"])archive/(\d{4}-\d{2}-\d{2})-audio/''')
        save(page, s, old)
    for path in sorted(glob.glob(os.path.join(REPO, 'archive', '*.html'))):
        name = os.path.basename(path)[:10]
        old = s = open(path, encoding='utf-8').read()
        s = sub_folders(s, r'''(['"])(\d{4}-\d{2}-\d{2})-audio/''')
        own = folder_url(name)
        if own:  # pages archived before the archive step rewrote 'audio/' to their own folder
            s = re.sub(r'''(['"])audio/(?!(?:mpeg|mp4|ogg|wav|webm|aac|x-)[a-z0-9.+-]*['"])''', lambda m: m.group(1) + own, s)
        save(path, s, old)
    feed = os.path.join(REPO, 'alexa-feed.json')
    if today and f'm/{today}' in up and os.path.exists(feed):
        old = s = open(feed, encoding='utf-8').read()
        s = re.sub(re.escape(GH_AUDIO) + r'wakeup-echo\.mp3(\?v=\d+)?', f'{URL}/m/{today}/wakeup-echo.mp3', s)
        save(feed, s, old)
    phone = os.path.join(REPO, 'wakeup.html')
    if up and os.path.exists(phone):
        old = s = open(phone, encoding='utf-8').read()
        s = re.sub(r'''(['"])audio/(?!(?:mpeg|mp4|ogg|wav|webm|aac|x-)[a-z0-9.+-]*['"])''', lambda m: m.group(1) + f'{URL}/latest/', s)
        save(phone, s, old)
    return changed


def publish(today):
    n = sync(today)
    print(f'sounds: {n} new files shrunk into sounds/public')
    ok = True
    try:
        deploy(choose(today, MORNING_EXTRA))
        if today:
            with open(os.path.join(REPO, 'audio', MARK), 'w') as f:
                f.write(f'm/{today}\n')
    except Exception as e:  # noqa: BLE001  (the pages still get re-pointed for what is online)
        print(f'sounds: upload failed: {e}')
        ok = False
    print('sounds: re-pointed', ', '.join(rewrite(today)) or 'nothing')
    print(f'sounds: {untrack()} mp3s taken out of git; {len(online())} of {len(staged())} folders online')
    return ok


def migrate(today=None):
    """Upload the backlog batch by batch (each about BATCH bytes) until every folder is online."""
    sync(today)
    fails = 0
    while True:
        want = choose(today, BATCH)
        if want <= online():
            break
        try:
            deploy(want)
            fails = 0
            print(f'sounds: {len(online())} of {len(staged())} folders online', flush=True)
        except Exception as e:  # noqa: BLE001
            fails += 1
            print(f'sounds: batch failed ({fails}/3): {str(e)[-200:]}', flush=True)
            if fails >= 3:
                return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['publish', 'migrate', 'rewrite', 'untrack', 'url', 'sync'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--today')
    a = ap.parse_args()
    if a.cmd == 'publish':
        sys.exit(0 if publish(a.today) else 1)
    if a.cmd == 'migrate':
        sys.exit(0 if migrate(a.today) else 1)
    if a.cmd == 'untrack':
        print(f'sounds: {untrack()} mp3s taken out of git')
    if a.cmd == 'sync':
        print(f'sounds: {sync(a.today)} new files shrunk')
    elif a.cmd == 'rewrite':
        print('re-pointed:', ', '.join(rewrite(a.today)) or 'nothing')
    elif a.cmd == 'url':
        print(f'{URL}/m/{a.args[0]}/{a.args[1]}')


if __name__ == '__main__':
    main()
