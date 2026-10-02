#!/usr/bin/env python3
"""fieldbed.py: the wake-up bed, made from real field recordings (2026-10-02).

Ben, 2026-10-02: "the digitally created sounds are artificial sounding ... pull up some actual sound
recordings that are readily available ... [they'll] create an element of intrigue behind the voice.
I found it was competing with the voice." This replaces soundscape.py's synthesized scenes.

The catalog (tools/fieldbeds.json, committed) lists real recordings, all CC0 or CC BY, with a caption
for the page and a credit line. The audio is cached in assets/field/ (gitignored); --fetch rebuilds
anything missing from the catalog's URLs. A morning never waits on the network: the pick only takes a
recording that is already cached, and downloads only if nothing at all is cached.

  fieldbed.py --list
  fieldbed.py --fetch                     download whatever the cache is missing (exit 1 if any fail)
  fieldbed.py --pick [--avoid a,b] [--seed N]
        -> id|caption|seed|credit|source
  fieldbed.py --render ID|random --seconds S --out bed.wav [--seed N] [--avoid a,b]
        [--voice START:END] [--carve DB] [--duck DB] [--lufs -29] [--fade-in 45] [--fade-out 20]
        -> writes the finished bed (44.1 kHz stereo float WAV) and prints the same info line

--avoid is the recent history, oldest first. Seasonal recordings ("months") only play in season, and
the most recent picks are held out, as many as the in-season pool allows while leaving three to choose
from (14 in October, fewer in winter when the pool is smaller).

Render: a seeded random stretch of the recording (a repeat is never the same stretch; recordings
shorter than the bed loop with an 8 s equal-power crossfade), high-pass per the catalog, events that
jump more than 8 dB over the body of the recording softened 3:1 (a crow, a moo, a bird at the mic),
loudness to -29 LUFS integrated (Ben's ear-tuned bed level, see garden-ambience-overlay), clicks and
pops held under -12 dBFS, the voice pocket, then a 45 s fade-in and a 20 s fade-out. daily-dashboard.sh limits and encodes the result.

The voice pocket: measured 2026-10-02, the synthesized brook that "competed with the voice" put 46%
of its energy in 1-4 kHz, where speech consonants live, and 78% of its loudness flutter at 3-12 Hz,
the rate of syllables, so the ear kept trying to hear words in it. The eth-garden bed Ben liked had
0% in that band. While the voice plays (--voice START:END) the bed crossfades to a copy with that band
carved out (--carve dB at 2 kHz, two octaves wide), and back again after. The overall level stays
put by default (--duck 0): Ben tuned the ~8 dB voice-over-bed gap by ear and rejected an 8 dB duck.
"""
import argparse, datetime, json, os, random, re, subprocess, sys, tempfile, urllib.request

import numpy as np
import soundfile as sf
from scipy import signal
from scipy.ndimage import minimum_filter1d, uniform_filter1d

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, 'fieldbeds.json')
CACHE = os.path.join(os.path.dirname(HERE), 'assets', 'field')
UA = {'User-Agent': 'daily-brief-fieldbed/1.0 (personal wake-up alarm)'}


def log(*a):
    print(*a, file=sys.stderr)


def catalog():
    with open(CATALOG) as f:
        return json.load(f)['recordings']


def cache_path(r):
    return os.path.join(CACHE, r['id'] + (os.path.splitext(r['audio'].split('?')[0])[1] or '.ogg'))


def probe_seconds(path):
    try:
        out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                             capture_output=True, text=True, timeout=30).stdout.strip()
        return float(out)
    except Exception:
        return 0.0


def cached(r):
    p = cache_path(r)
    return os.path.exists(p) and probe_seconds(p) > 10


def download(r, timeout=120):
    """Fetch a recording into the cache. Freesound's CDN serves previews at ~80 KB/s per connection, so
    only the part the catalog uses is requested (`bytes`, a Range request), then remuxed without
    re-encoding so the cached file ends cleanly."""
    path = cache_path(r)
    ext = os.path.splitext(path)[1]
    part, tmp = path + '.part' + ext, path + '.tmp' + ext
    os.makedirs(CACHE, exist_ok=True)
    try:
        headers = dict(UA)
        if r.get('bytes'):
            headers['Range'] = f'bytes=0-{int(r["bytes"]) - 1}'
        with urllib.request.urlopen(urllib.request.Request(r['audio'], headers=headers), timeout=timeout) as resp, \
                open(part, 'wb') as f:
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', part, '-c', 'copy', tmp],
                       capture_output=True, check=True, timeout=300)
        if probe_seconds(tmp) <= 10:
            raise ValueError('downloaded file does not decode')
        os.replace(tmp, path)
        log(f'fetched {r["id"]} ({os.path.getsize(path) // 1024} KB, {probe_seconds(path):.0f} s)')
        return True
    except Exception as e:
        log(f'fetch failed for {r["id"]}: {e}')
        return False
    finally:
        for p in (part, tmp):
            if os.path.exists(p):
                os.remove(p)


def credit(r):
    return f'recorded by {r["by"]}, {r["license"]}'


def info_line(r, seed):
    clean = lambda s: str(s).replace('|', '/').replace('\n', ' ').strip()
    return '|'.join(clean(v) for v in (r['id'], r['caption'], seed, credit(r), r['source']))


def candidates(recs, recent, month):
    """In-season recordings minus the most recently heard, holding out as many as the pool allows
    while leaving at least three to choose from."""
    pool = [r for r in recs if not r.get('months') or month in r['months']] or list(recs)
    ids = {r['id'] for r in pool}
    recent = [i for i in recent if i in ids]
    k = max(0, min(len(recent), len(pool) - 3))
    held = set(recent[len(recent) - k:])
    return [r for r in pool if r['id'] not in held]


def choose(recs, recent, rng, prefer=None):
    """`prefer` if it is usable, else a random eligible recording. Cached ones first; the network is
    only tried when nothing usable is cached."""
    month = int(os.environ.get('FIELDBED_MONTH') or datetime.date.today().month)
    order = candidates(recs, recent, month)
    rng.shuffle(order)
    rest = [r for r in recs if r not in order]
    rng.shuffle(rest)
    order += rest
    if prefer:
        order = [r for r in recs if r['id'] == prefer] + [r for r in order if r['id'] != prefer]
    found = next((r for r in order if cached(r)), None) or next((r for r in order if download(r)), None)
    if found and prefer and found['id'] != prefer:
        log(f'{prefer} unavailable; using {found["id"]}')
    return found


def decode(path, ss=0.0, t=None):
    cmd = ['ffmpeg', '-v', 'error']
    if ss > 0:
        cmd += ['-ss', f'{ss:.3f}']
    if t:
        cmd += ['-t', f'{t:.3f}']
    raw = subprocess.run(cmd + ['-i', path, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True, timeout=300).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)


def span(r):
    """Usable seconds of the cached recording, per the catalog's start/end trims."""
    dur = probe_seconds(cache_path(r))
    start, end = float(r.get('start') or 0), float(r.get('end') or 0)
    stop = dur + end if end < 0 else (min(end, dur) if end > 0 else dur)
    return start, max(start, stop)


def load(r, t0, t1):
    """Decode [t0, t1) seconds, high/low-passed per the catalog (1 s of filter pre-roll discarded)."""
    pre = min(1.0, t0)
    x = decode(cache_path(r), t0 - pre, t1 - t0 + pre)
    hp = r.get('hp', 60)
    if hp:
        x = signal.sosfilt(signal.butter(2, hp, 'highpass', fs=SR, output='sos'), x, axis=0)
    if r.get('lp'):
        x = signal.sosfilt(signal.butter(2, r['lp'], 'lowpass', fs=SR, output='sos'), x, axis=0)
    return x[int(pre * SR):]


def window(x, n, rng):
    """Exactly n samples: a random stretch of x, or x looped with an equal-power crossfade if it is short."""
    if len(x) >= n:
        off = int(rng.integers(0, len(x) - n + 1))
        return x[off:off + n].copy()
    if len(x) >= n - SR // 2:  # a decode a hair short: pad inside the fade-out
        return np.pad(x, ((0, n - len(x)), (0, 0)))
    xf = int(min(8 * SR, len(x) // 4))
    t = np.linspace(0, np.pi / 2, xf)[:, None]
    fade_out, fade_in = np.cos(t), np.sin(t)
    off = int(rng.integers(0, len(x) - xf))
    y = x[off:].copy()
    while len(y) < n:
        y = np.concatenate([y[:-xf], y[-xf:] * fade_out + x[:xf] * fade_in, x[xf:]])
    return y[:n]


def tame(x, over_db=8.0, ratio=3.0, attack=0.3, release=2.5):
    """Soften events that jump well above the body of the recording: a slow compressor on 400 ms RMS
    whose threshold sits over_db above the median level. Steady recordings pass through untouched."""
    if over_db <= 0 or len(x) < SR:
        return x
    hop, win = int(0.1 * SR), int(0.4 * SR)
    p = np.concatenate([[0.0], np.cumsum(x.mean(axis=1) ** 2)])
    centers = np.arange(0, len(x), hop)
    lo, hi = np.clip(centers - win // 2, 0, len(x)), np.clip(centers + win // 2, 0, len(x))
    lvl = 10 * np.log10((p[hi] - p[lo]) / np.maximum(hi - lo, 1) + 1e-12)
    over = np.maximum(lvl - (np.median(lvl) + over_db), 0) * (1 - 1 / ratio)
    a_att, a_rel = np.exp(-0.1 / attack), np.exp(-0.1 / release)
    g, smooth = 0.0, np.empty_like(over)
    for i, v in enumerate(over):
        c = a_att if v > g else a_rel
        g = c * g + (1 - c) * v
        smooth[i] = g
    return x * (10 ** (-np.interp(np.arange(len(x)), centers, smooth) / 20))[:, None]


def limit(x, ceiling_db=-12.0, ms=25):
    """Peak limiter for clicks and pops (an ice crack, a fire pop, a slap of water at the mic): the
    gain each sample needs is held over a 25 ms window and then smoothed across it, so a transient
    comes down to the ceiling, 17 dB over the -29 LUFS body, without pumping the rest of the bed."""
    need = np.minimum(1.0, 10 ** (ceiling_db / 20) / np.maximum(np.abs(x).max(axis=1), 1e-12))
    if need.min() >= 1.0:
        return x
    w = max(3, int(ms * SR / 1000) | 1)
    return x * uniform_filter1d(minimum_filter1d(need, size=w), size=w)[:, None]


def integrated_lufs(x):
    """EBU R128 integrated loudness via ffmpeg (the same meter the old pipeline used)."""
    fd, tmp = tempfile.mkstemp(suffix='.wav')
    os.close(fd)
    try:
        sf.write(tmp, x.astype(np.float32), SR, subtype='FLOAT')
        err = subprocess.run(['ffmpeg', '-nostats', '-i', tmp, '-af', 'ebur128=framelog=quiet', '-f', 'null', '-'],
                             capture_output=True, text=True, timeout=300).stderr
        vals = re.findall(r'^\s+I:\s+(-?[0-9.]+) LUFS', err, re.M)
        return float(vals[-1]) if vals else None
    finally:
        os.remove(tmp)


def peaking_sos(f0, gain_db, bw_oct):
    """RBJ cookbook peaking EQ as one second-order section."""
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / SR
    alpha = np.sin(w0) * np.sinh(np.log(2) / 2 * bw_oct * w0 / np.sin(w0))
    b = np.array([1 + alpha * A, -2 * np.cos(w0), 1 - alpha * A])
    a = np.array([1 + alpha / A, -2 * np.cos(w0), 1 - alpha / A])
    return np.concatenate([b / a[0], a / a[0]])[None, :]


def ramp(n, pts):
    """Piecewise-linear weight over sample times; pts = [(seconds, value), ...] in time order."""
    t = np.arange(n) / SR
    xs, ys = [], []
    for x, y in pts:  # np.interp needs strictly increasing x; nudge any ties forward
        xs.append(max(float(x), xs[-1] + 1e-6) if xs else float(x))
        ys.append(y)
    return np.interp(t, xs, ys)


def pocket(x, vs, ve, carve_db, duck_db):
    if carve_db <= 0 and duck_db <= 0:
        return x
    w = ramp(len(x), [(0, 0), (max(vs - 3, 0), 0), (vs, 1), (ve, 1), (ve + 4, 0), (len(x) / SR + 1, 0)])[:, None]
    y = x
    if carve_db > 0:
        carved = signal.sosfilt(peaking_sos(2000, -carve_db, 2.0), x, axis=0)
        y = (1 - w) * x + w * carved
    if duck_db > 0:
        y = y * 10 ** (-duck_db * w / 20)
    return y


def envelope(x, fade_in, fade_out):
    total = len(x) / SR
    fi, fo = min(fade_in, total / 3), min(fade_out, total / 3)
    return x * ramp(len(x), [(0, 0), (fi, 1), (total - fo, 1), (total, 0)])[:, None]


def render(args):
    recs = catalog()
    seed = args.seed if args.seed is not None else int.from_bytes(os.urandom(4), 'big')
    rng = np.random.default_rng(seed)
    prefer = None if args.render == 'random' else args.render
    if prefer and prefer not in {r['id'] for r in recs}:
        sys.exit(f'unknown recording {prefer!r}; try --list')
    r = choose(recs, [s.strip() for s in args.avoid.split(',') if s.strip()], random.Random(seed), prefer)
    if r is None:
        sys.exit('no recording available (cache empty and downloads failed)')
    start, stop = span(r)
    if stop - start >= args.seconds + 1:
        off = start + float(rng.uniform(0, stop - start - args.seconds - 1))
        x = load(r, off, off + args.seconds + 1)
    else:
        x = load(r, start, stop)
    x = tame(window(x, int(round(args.seconds * SR)), rng), float(r.get('tame', 8)))
    lufs = integrated_lufs(x)
    if lufs is None or lufs < -70:
        sys.exit(f'could not measure {r["id"]}')
    x *= 10 ** ((args.lufs + float(r.get('gain_db') or 0) - lufs) / 20)
    x = limit(x)
    if args.voice:
        vs, ve = (float(v) for v in args.voice.split(':'))
        x = pocket(x, vs, ve, args.carve, args.duck)
    x = envelope(x, args.fade_in, args.fade_out)
    sf.write(args.out, x.astype(np.float32), SR, subtype='FLOAT')
    print(info_line(r, seed))


def main():
    ap = argparse.ArgumentParser(description='Wake-up bed from real field recordings.')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--fetch', action='store_true')
    ap.add_argument('--pick', action='store_true')
    ap.add_argument('--render', '--scene', dest='render', default=None)
    ap.add_argument('--seconds', type=float, default=300)
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--avoid', default='', help='recently played ids, oldest first, comma-separated')
    ap.add_argument('--out', default=None)
    ap.add_argument('--voice', default=None, help='START:END seconds of the voice inside the bed')
    ap.add_argument('--carve', type=float, default=6.0, help='dB cut at 1-4 kHz while the voice plays')
    ap.add_argument('--duck', type=float, default=0.0, help='dB level drop while the voice plays')
    ap.add_argument('--lufs', type=float, default=-29.0)
    ap.add_argument('--fade-in', type=float, default=45.0)
    ap.add_argument('--fade-out', type=float, default=20.0)
    a = ap.parse_args()
    recs = catalog()
    if a.list:
        for r in recs:
            start, stop = span(r) if cached(r) else (0, 0)
            months = ','.join(map(str, r['months'])) if r.get('months') else 'all year'
            print(f'{r["id"]:20s} {stop - start:5.0f}s  {months:14s} {r["caption"]}  ({credit(r)})')
        return
    if a.fetch:
        bad = [r['id'] for r in recs if not cached(r) and not download(r)]
        print(f'{len(recs) - len(bad)}/{len(recs)} cached' + (f'; failed: {", ".join(bad)}' if bad else ''))
        sys.exit(1 if bad else 0)
    if a.pick:
        seed = a.seed if a.seed is not None else int.from_bytes(os.urandom(4), 'big')
        r = choose(recs, [s.strip() for s in a.avoid.split(',') if s.strip()], random.Random(seed))
        if r is None:
            sys.exit('no recording available')
        print(info_line(r, seed))
        return
    if a.render:
        if not a.out:
            sys.exit('--out required to render')
        render(a)
        return
    ap.print_help()


if __name__ == '__main__':
    main()
