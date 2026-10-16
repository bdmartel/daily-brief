#!/usr/bin/env python3
"""poem_split.py: cut a morning's poem.mp3 into its two readings (2026-10-15).

Ben, 2026-10-15: "give an option where it's POEM, LESSON, POEM as a way to digest it". Since
2026-09-13 the spoken poem is one take read twice: the reading, 1.5 s of silence, the same reading
again, then "So — up!" once. The page's "poem · lesson · poem" button needs the two readings apart:
  poem-first.mp3   the first reading alone (no closer)
  poem-again.mp3   the second reading with "So — up!", so the closer still comes once, at the end
The morning script writes both from its own pieces. This rebuilds them from poem.mp3 alone, for
mornings made before that: it finds where the take starts over (the lag at which the file best
matches itself) and cuts in the silence between the readings.

  poem_split.py archive/2026-10-14-audio [more folders] [--check] [--force]

--check prints what it found and writes nothing. A folder whose poem.mp3 is a single reading
(before 2026-09-13, or a fallback morning) is left alone.
"""
import argparse, os, subprocess, sys
import numpy as np

SR = 24000       # narrate's output rate (mono)
PAD = 1.5        # silence between the readings (daily-dashboard.sh: apad=pad_dur=1.5)
MATCH = 0.5      # how alike the halves must be: 0.90-0.98 for the 32 doubled mornings, under 0.07 for singles


def decode(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def repeat_lag(x):
    """(lag in samples where the take starts over, how alike the two copies are, 0-1)."""
    n = len(x)
    size = 1 << int(np.ceil(np.log2(2 * n)))
    spec = np.fft.rfft(x, size)
    r = np.fft.irfft(spec * np.conj(spec), size)[:n]
    e = np.concatenate(([0.0], np.cumsum(x * x)))
    lags = np.arange(int(0.3 * n), int(0.7 * n))
    norm = r[lags] / np.sqrt(np.maximum(e[n - lags] * (e[n] - e[lags]), 1e-20))
    k = int(np.argmax(norm))
    return int(lags[k]), float(norm[k])


def encode(samples, path):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                    '-c:a', 'libmp3lame', '-b:a', '128k', path],
                   input=samples.astype(np.float32).tobytes(), check=True)


def split(folder, check=False, force=False):
    src = os.path.join(folder, 'poem.mp3')
    first, again = os.path.join(folder, 'poem-first.mp3'), os.path.join(folder, 'poem-again.mp3')
    if not os.path.exists(src):
        return f'{folder}: no poem.mp3'
    if not force and not check and os.path.exists(first) and os.path.exists(again):
        return f'{folder}: already split'
    x = decode(src)
    lag, match = repeat_lag(x)
    gap = x[lag - int(PAD * SR):lag]
    gap_db = 20 * np.log10(max(np.sqrt(np.mean(gap * gap)), 1e-10))
    info = f'repeat at {lag / SR:.2f} s of {len(x) / SR:.2f} s, match {match:.3f}, pause {gap_db:.0f} dB'
    if match < MATCH or gap_db > -60:            # the pause is digital silence (-160 dB and below)
        return f'{folder}: single reading, left alone ({info})'
    if check:
        return f'{folder}: would split ({info})'
    end = lag - int(PAD * SR) + int(0.25 * SR)   # the first reading, plus a quarter second of the pause
    encode(x[:end], first)
    encode(x[lag - int(0.1 * SR):], again)       # the second reading and the closer
    return f'{folder}: split ({info})'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folders', nargs='+')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    for f in a.folders:
        try:
            print(split(f.rstrip('/'), a.check, a.force))
        except subprocess.CalledProcessError as e:
            print(f'{f}: ffmpeg failed ({e})', file=sys.stderr)


if __name__ == '__main__':
    main()
