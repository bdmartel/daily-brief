#!/usr/bin/env python3
"""soundscape.py — a different wake-up sound every morning (Ben, 2026-09-22).

Fourteen procedurally generated scenes, each randomized every time it is rendered, so no two
mornings sound the same. Everything is synthesized offline with numpy/scipy (no samples, no
network, no cost); the "garden" scene shells out to tools/ethgarden-render.mjs with a fresh seed.

  soundscape.py --list
  soundscape.py --pick [--avoid rain,wind] [--seed N]          -> prints  scene|description|seed
  soundscape.py --scene NAME|random --seconds S --out bed.wav [--seed N] [--avoid a,b]
                                                              -> renders, prints scene|description|seed

Output: 44.1 kHz stereo 16-bit WAV at RMS -20 dBFS, soft-clipped. Loudness (-29 LUFS) and the
wake-up fade envelope are applied afterwards by daily-dashboard.sh with ffmpeg, the same way the
fixed garden asset used to be trimmed. Scenes that fail fall back to another scene, and the caller
falls back to assets/garden-ambience.mp3 if this script fails entirely.
"""
import argparse, math, os, subprocess, sys, tempfile
import numpy as np
from scipy import signal
import soundfile as sf

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))

SCENES = {
    'rain':     'rain on the roof',
    'wind':     'wind in the pines',
    'stream':   'a brook over stones',
    'ocean':    'waves on a shore',
    'chimes':   'wind chimes',
    'bowl':     'a singing bowl',
    'crickets': 'a night meadow',
    'fire':     'a woodstove, ticking and crackling',
    'kalimba':  'a music box, one note at a time',
    'bells':    'bells from across a valley',
    'birds':    'birds at first light',
    'pad':      'a slow chord, breathing',
    'cave':     'water drops in a stone room',
    'garden':   "Jackson's garden, a new performance",
}

# ----------------------------------------------------------------------------- helpers

def colored(rng, n, exponent):
    """1/f^exponent noise via FFT shaping. exponent 0 = white, 1 = pink, 2 = brown. Peak 1."""
    x = rng.standard_normal(n).astype(np.float32)
    if exponent == 0:
        return x / (np.abs(x).max() + 1e-9)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    f[0] = f[1]
    X *= (f / 20.0) ** (-exponent / 2)
    y = np.fft.irfft(X, n).astype(np.float32)
    return y / (np.abs(y).max() + 1e-9)

def sos_bp(lo, hi, order=4):
    lo = max(20.0, lo); hi = min(SR / 2 - 100, hi)
    return signal.butter(order, [lo, hi], btype='bandpass', fs=SR, output='sos')

def sos_lp(fc, order=4):
    return signal.butter(order, min(fc, SR / 2 - 100), btype='lowpass', fs=SR, output='sos')

def sos_hp(fc, order=4):
    return signal.butter(order, max(fc, 10.0), btype='highpass', fs=SR, output='sos')

def filt(sos, x):
    return signal.sosfilt(sos, x.astype(np.float32)).astype(np.float32)

def walk(rng, n, tau_s):
    """Smooth random modulation in [0, 1] at audio rate (built at 100 Hz, interpolated)."""
    lr = 100
    m = int(n / SR * lr) + 4
    steps = rng.standard_normal(m)
    a = 1.0 / max(1.0, tau_s * lr)
    y = signal.lfilter([a], [1, -(1 - a)], steps)
    y = y[int(min(m - 1, 3 * tau_s * lr)):]  # drop the settle-in
    if len(y) < 4:
        y = steps
    y = (y - y.min()) / (y.max() - y.min() + 1e-9)
    t = np.linspace(0, n / SR, len(y))
    return np.interp(np.arange(n) / SR, t, y).astype(np.float32)

def sines_env(rng, n, periods_s, lo=0.3, hi=1.0):
    """Sum of a few slow sines with random phases, mapped to [lo, hi]."""
    t = np.arange(n, dtype=np.float32) / SR
    e = np.zeros(n, np.float32)
    for p in periods_s:
        e += np.sin(2 * np.pi * t / p + rng.uniform(0, 2 * np.pi)).astype(np.float32)
    e = (e - e.min()) / (e.max() - e.min() + 1e-9)
    return (lo + (hi - lo) * e).astype(np.float32)

def tv_bandpass(x, center_hz, bw_oct, block=4096):
    """Time-varying Gaussian band-pass (in log frequency) via overlap-add STFT."""
    hop = block // 2
    win = np.hanning(block).astype(np.float32)
    n = len(x)
    out = np.zeros(n + block, np.float32)
    freqs = np.fft.rfftfreq(block, 1 / SR)
    logf = np.log2(np.maximum(freqs, 20.0))
    nblocks = max(1, (n - block) // hop + 1)
    idx = (np.arange(nblocks) * hop + block // 2).clip(0, n - 1)
    cs = np.log2(np.maximum(center_hz[idx], 20.0))
    for b in range(nblocks):
        s = b * hop
        seg = x[s:s + block]
        if len(seg) < block:
            seg = np.pad(seg, (0, block - len(seg)))
        S = np.fft.rfft(seg * win)
        g = np.exp(-0.5 * ((logf - cs[b]) / bw_oct) ** 2)
        out[s:s + block] += (np.fft.irfft(S * g, block) * win).astype(np.float32)
    return out[:n]

def reverb(x, rng, decay_s=2.5, wet=0.4, tone_hz=4000.0, predelay_s=0.02):
    """Decaying-noise convolution reverb (the same idea as the garden's), applied per channel."""
    n_ir = int(decay_s * SR)
    t = np.arange(n_ir) / SR
    ir = (rng.standard_normal(n_ir) * np.exp(-t * (6.9 / decay_s))).astype(np.float32)
    ir = filt(sos_lp(tone_hz, 2), ir)
    ir = np.concatenate([np.zeros(int(predelay_s * SR), np.float32), ir])
    ir /= (np.sqrt((ir ** 2).sum()) + 1e-9)
    def one(ch):
        w = signal.fftconvolve(ch, ir)[:len(ch)].astype(np.float32)
        w *= (np.abs(ch).max() + 1e-9) / (np.abs(w).max() + 1e-9)
        return (ch * (1 - wet) + w * wet).astype(np.float32)
    if x.ndim == 1:
        return one(x)
    return np.stack([one(x[:, 0]), one(x[:, 1])], axis=1)

def strike(freq, dur, partials, decay, amp=1.0, attack_s=0.004, detune=0.0):
    """Additive struck/plucked tone. partials = [(ratio, amplitude, decay_multiplier), ...]"""
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    y = np.zeros(n, np.float32)
    for ratio, a, dm in partials:
        f = freq * ratio * (1 + detune)
        if f > SR / 2 - 500:
            continue
        y += (a * np.sin(2 * np.pi * f * t) * np.exp(-t / (decay * dm))).astype(np.float32)
    att = max(1, int(attack_s * SR))
    y[:att] *= np.linspace(0, 1, att, dtype=np.float32)
    return y * amp

def place(buf, y, start_s, pan=0.0, gain=1.0):
    """Add mono event y into stereo buf at start_s with constant-power pan (-1..1)."""
    s = int(start_s * SR)
    if s >= len(buf) or s < 0:
        return
    e = min(len(buf), s + len(y))
    seg = y[:e - s] * gain
    ang = (pan + 1) * math.pi / 4
    buf[s:e, 0] += seg * math.cos(ang)
    buf[s:e, 1] += seg * math.sin(ang)

def stereo_noise(rng, n, exponent):
    return np.stack([colored(rng, n, exponent), colored(rng, n, exponent)], axis=1)

def wide(mono, rng, amount=0.15):
    """Mono bed -> slightly wide stereo by mixing in a decorrelated copy."""
    other = np.roll(mono, int(0.011 * SR))
    l = mono + amount * other
    r = mono - amount * other
    return np.stack([l, r], axis=1).astype(np.float32)

SCALES = {
    'penta_major': [0, 2, 4, 7, 9],
    'penta_minor': [0, 3, 5, 7, 10],
    'hirajoshi':   [0, 2, 3, 7, 8],
    'lydian_ish':  [0, 2, 4, 6, 7, 9, 11],
    'dorian':      [0, 2, 3, 5, 7, 9, 10],
}

def scale_freqs(rng, root_hz, octaves=2, scale=None):
    name = scale or rng.choice(list(SCALES))
    degs = SCALES[name]
    out = []
    for o in range(octaves + 1):
        for d in degs:
            out.append(root_hz * 2 ** ((d + 12 * o) / 12))
    return name, out

def poisson_times(rng, total_s, mean_gap_fn, start=0.0):
    t = start + rng.exponential(mean_gap_fn(start))
    while t < total_s:
        yield t
        t += rng.exponential(max(0.05, mean_gap_fn(t)))

# ----------------------------------------------------------------------------- scenes

def sc_rain(rng, n):
    T = n / SR
    out = np.zeros((n, 2), np.float32)
    body = stereo_noise(rng, n, 1.0)
    lo, hi = rng.uniform(350, 700), rng.uniform(4500, 8000)
    for c in range(2):
        body[:, c] = filt(sos_bp(lo, hi, 2), body[:, c])
    level = 0.55 + 0.45 * walk(rng, n, rng.uniform(6, 14))
    body *= level[:, None]
    out += body / (np.abs(body).max() + 1e-9)
    # drips
    rate = rng.uniform(1.0, 4.0)
    for t in poisson_times(rng, T, lambda _: 1.0 / rate):
        dl = int(rng.uniform(0.006, 0.025) * SR)
        b = rng.standard_normal(dl).astype(np.float32) * np.exp(-np.arange(dl) / (dl * 0.3))
        fc = rng.uniform(1500, 5000)
        b = filt(sos_bp(fc / 1.4, fc * 1.4, 2), b)
        place(out, b / (np.abs(b).max() + 1e-9), t, rng.uniform(-0.9, 0.9), rng.uniform(0.08, 0.35))
    # distant thunder, sometimes
    if rng.random() < 0.35:
        for _ in range(rng.integers(2, 5)):
            dl = int(rng.uniform(3, 7) * SR)
            b = colored(rng, dl, 2.0)
            b = filt(sos_bp(28, 180, 2), b)
            tt = np.arange(dl) / SR
            env = (1 - np.exp(-tt / rng.uniform(0.3, 1.2))) * np.exp(-tt / rng.uniform(1.5, 3.0))
            b = b * env.astype(np.float32)
            place(out, b / (np.abs(b).max() + 1e-9), rng.uniform(5, T - 8), rng.uniform(-0.5, 0.5), rng.uniform(0.5, 0.9))
    return out

def sc_wind(rng, n):
    out = np.zeros((n, 2), np.float32)
    gust = walk(rng, n, rng.uniform(4, 8))
    gust = (0.3 + 0.7 * gust ** 1.4).astype(np.float32)
    center = (rng.uniform(220, 320) * 2 ** (walk(rng, n, rng.uniform(5, 9)) * rng.uniform(2.0, 2.8))).astype(np.float32)
    for c in range(2):
        x = colored(rng, n, 0.0)
        y = tv_bandpass(x, center, rng.uniform(0.7, 1.0))
        y *= gust if c == 0 else np.roll(gust, int(0.25 * SR))
        out[:, c] += y / (np.abs(y).max() + 1e-9)
    # whistle through a gap
    fc = rng.uniform(1800, 3400)
    w = filt(sos_bp(fc / 1.08, fc * 1.08, 6), colored(rng, n, 0.0))
    w *= (gust ** 3) * 0.18
    out += wide(w, rng, 0.3) / (np.abs(w).max() + 1e-9) * 0.18
    # low rumble
    r = filt(sos_lp(110, 2), colored(rng, n, 2.0)) * gust * 0.35
    out[:, 0] += r; out[:, 1] += r
    return out

def sc_stream(rng, n):
    out = np.zeros((n, 2), np.float32)
    t = np.arange(n, dtype=np.float32) / SR
    centers = np.array([700, 1400, 2600, 4200]) * rng.uniform(0.8, 1.25, 4)
    for i, fc in enumerate(centers):
        x = filt(sos_bp(fc / 1.35, fc * 1.35, 2), colored(rng, n, 0.0))
        fl = rng.uniform(5, 14)
        flutter = 1 + 0.55 * np.sin(2 * np.pi * fl * t + 6 * walk(rng, n, 0.7)).astype(np.float32)
        x *= flutter * (0.5 + 0.5 * walk(rng, n, rng.uniform(0.8, 2.0)))
        place(out, x / (np.abs(x).max() + 1e-9), 0.0, rng.uniform(-0.7, 0.7), rng.uniform(0.5, 1.0) / (i + 1) ** 0.4)
    g = filt(sos_bp(80, 350, 2), colored(rng, n, 2.0)) * (0.4 + 0.6 * walk(rng, n, 0.4))
    out += wide(g / (np.abs(g).max() + 1e-9), rng, 0.2) * 0.5
    return out

def sc_ocean(rng, n):
    T = n / SR
    lr = 100
    P = rng.uniform(9, 14)
    env = np.zeros(int(T * lr) + lr, np.float32)
    pos = 0.0
    while pos < T + 2:
        p = P * rng.uniform(0.8, 1.2); a = rng.uniform(0.45, 1.0)
        L = int(p * lr); rise = int(L * 0.42)
        shape = np.concatenate([np.sin(np.linspace(0, np.pi / 2, rise)) ** 2,
                                np.cos(np.linspace(0, np.pi / 2, L - rise)) ** 1.6])
        s = int(pos * lr)
        e = min(len(env), s + L)
        env[s:e] = np.maximum(env[s:e], (a * shape[:e - s]).astype(np.float32))
        pos += p * rng.uniform(0.85, 1.0)
    tgrid = np.arange(len(env)) / lr
    E = np.interp(np.arange(n) / SR, tgrid, env).astype(np.float32)
    E = (0.12 + 0.88 * E)
    out = np.zeros((n, 2), np.float32)
    for c in range(2):
        body = filt(sos_lp(rng.uniform(700, 1200), 2), colored(rng, n, 1.0)) * E
        foam = filt(sos_hp(rng.uniform(1400, 2200), 2), colored(rng, n, 0.0)) * (E ** 3) * 0.6
        y = body / (np.abs(body).max() + 1e-9) + foam / (np.abs(foam).max() + 1e-9) * 0.45
        out[:, c] = y
    return out

def sc_chimes(rng, n):
    T = n / SR
    out = np.zeros((n, 2), np.float32)
    name, freqs = scale_freqs(rng, rng.uniform(440, 780), octaves=1)
    tubes = sorted(rng.choice(freqs, size=min(len(freqs), rng.integers(5, 8)), replace=False))
    gust = walk(rng, n, rng.uniform(5, 9))
    decay = rng.uniform(2.5, 5.0)
    parts = [(1, 1.0, 1.0), (2.76, 0.5, 0.6), (5.40, 0.22, 0.35), (8.93, 0.10, 0.2)]
    def gap(t):
        g = gust[min(n - 1, int(t * SR))]
        return 0.9 + 7.0 * (1 - g) ** 1.5
    last = None
    for t in poisson_times(rng, T, gap, start=rng.uniform(2, 8)):
        if last is None or rng.random() < 0.4:
            i = rng.integers(0, len(tubes))
        else:
            i = int(np.clip(last + rng.integers(-1, 2), 0, len(tubes) - 1))
        last = i
        g = gust[min(n - 1, int(t * SR))]
        y = strike(tubes[i], decay * 1.6, parts, decay, amp=1.0, detune=rng.uniform(-0.002, 0.002))
        place(out, y, t, -0.7 + 1.4 * i / max(1, len(tubes) - 1), rng.uniform(0.25, 0.7) * (0.5 + 0.5 * g))
    out /= (np.abs(out).max() + 1e-9)
    w = tv_bandpass(colored(rng, n, 0.0), (rng.uniform(350, 550) * 2 ** (walk(rng, n, 6) * 1.5)).astype(np.float32), 0.9)
    w *= (0.25 + 0.75 * gust)
    out += wide(w / (np.abs(w).max() + 1e-9), rng, 0.3) * 0.16
    return reverb(out, rng, decay_s=2.6, wet=0.4, tone_hz=5000)

def sc_bowl(rng, n):
    t = np.arange(n, dtype=np.float32) / SR
    f0 = rng.uniform(110, 260)
    parts = [(1, 1.0), (2.71, 0.45), (4.86, 0.22), (7.40, 0.10)]
    y = np.zeros(n, np.float32)
    for r, a in parts:
        beat = rng.uniform(0.25, 1.3)
        y += (a * 0.5 * (np.sin(2 * np.pi * f0 * r * t) + np.sin(2 * np.pi * (f0 * r + beat) * t + rng.uniform(0, 6.28)))).astype(np.float32)
    env = sines_env(rng, n, [rng.uniform(17, 26), rng.uniform(28, 45)], 0.35, 1.0)
    y *= env
    out = wide(y / (np.abs(y).max() + 1e-9), rng, 0.2)
    T = n / SR
    for ts in poisson_times(rng, T, lambda _: rng.uniform(25, 60), start=rng.uniform(4, 20)):
        s = strike(f0, 6.0, [(1, 1.0, 1.0), (2.71, 0.5, 0.7), (4.86, 0.3, 0.45), (7.4, 0.15, 0.3)], 2.8, amp=1.0, attack_s=0.03)
        place(out, s, ts, rng.uniform(-0.2, 0.2), rng.uniform(0.35, 0.7))
    out = np.stack([filt(sos_lp(3200, 2), out[:, 0]), filt(sos_lp(3200, 2), out[:, 1])], axis=1)
    return reverb(out, rng, decay_s=3.2, wet=0.35, tone_hz=3500)

def sc_crickets(rng, n):
    t = np.arange(n, dtype=np.float32) / SR
    out = np.zeros((n, 2), np.float32)
    m = rng.integers(4, 9)
    lr = 1000
    for _ in range(m):
        f = rng.uniform(3400, 5200); pr = rng.uniform(22, 40)
        npulse = rng.integers(3, 7); gap_s = rng.uniform(0.3, 1.1)
        chirp_len = npulse / pr
        # gate at 1 kHz
        g = np.zeros(int(n / SR * lr) + 2, np.float32)
        pos = rng.uniform(0, 3)
        T = n / SR
        while pos < T:
            s = int(pos * lr); e = min(len(g), s + int(chirp_len * lr))
            g[s:e] = 1.0
            pos += chirp_len + gap_s * rng.uniform(0.85, 1.15)
            if rng.random() < 0.05:
                pos += rng.uniform(2, 6)  # a pause
        gate = np.interp(np.arange(n) / SR, np.arange(len(g)) / lr, g).astype(np.float32)
        pulses = np.clip(np.sin(2 * np.pi * pr * t + rng.uniform(0, 6.28)) * 1.5, 0, 1).astype(np.float32)
        y = np.sin(2 * np.pi * f * t + 0.01 * np.sin(2 * np.pi * 7 * t)).astype(np.float32) * pulses * gate
        place(out, y, 0.0, rng.uniform(-0.9, 0.9), rng.uniform(0.15, 0.55))
    out /= (np.abs(out).max() + 1e-9)
    breeze = filt(sos_bp(180, 1600, 2), colored(rng, n, 1.0)) * (0.3 + 0.7 * walk(rng, n, 7))
    out += wide(breeze / (np.abs(breeze).max() + 1e-9), rng, 0.3) * 0.22
    return np.stack([filt(sos_lp(8000, 2), out[:, 0]), filt(sos_lp(8000, 2), out[:, 1])], axis=1)

def sc_fire(rng, n):
    T = n / SR
    out = np.zeros((n, 2), np.float32)
    bed = filt(sos_lp(260, 2), colored(rng, n, 2.0)) * (0.55 + 0.45 * walk(rng, n, 0.35))
    out += wide(bed / (np.abs(bed).max() + 1e-9), rng, 0.15) * 0.55
    dens = walk(rng, n, 5)
    def gap(t):
        return 1.0 / (2.0 + 6.0 * dens[min(n - 1, int(t * SR))])
    for t in poisson_times(rng, T, gap):
        dl = int(rng.uniform(0.0008, 0.006) * SR) + 8
        b = rng.standard_normal(dl).astype(np.float32) * np.exp(-np.arange(dl) / (dl * 0.4))
        fc = rng.uniform(1500, 5000)
        b = filt(sos_hp(fc, 2), b)
        amp = float(np.clip(rng.lognormal(-1.6, 0.6), 0.02, 0.9))
        place(out, b / (np.abs(b).max() + 1e-9), t, rng.uniform(-0.4, 0.4), amp)
    for t in poisson_times(rng, T, lambda _: rng.uniform(3, 9), start=rng.uniform(1, 5)):
        dl = int(rng.uniform(0.02, 0.045) * SR)
        b = rng.standard_normal(dl).astype(np.float32) * np.exp(-np.arange(dl) / (dl * 0.25))
        b = filt(sos_bp(300, 1400, 2), b)
        place(out, b / (np.abs(b).max() + 1e-9), t, rng.uniform(-0.3, 0.3), rng.uniform(0.4, 0.8))
    hiss = filt(sos_bp(3000, 8500, 2), colored(rng, n, 0.0)) * walk(rng, n, 2) * 0.05
    out[:, 0] += hiss; out[:, 1] += np.roll(hiss, 300)
    return out

def sc_kalimba(rng, n):
    T = n / SR
    out = np.zeros((n, 2), np.float32)
    name, freqs = scale_freqs(rng, rng.uniform(196, 392), octaves=2)
    base = rng.uniform(0.7, 1.6)
    decay = rng.uniform(1.5, 2.8)
    parts = [(1, 1.0, 1.0), (2, 0.35, 0.6), (3, 0.14, 0.4), (5.4, 0.07, 0.2)]
    i = rng.integers(0, len(freqs)); t = rng.uniform(1.5, 4.0); k = 0
    while t < T - 3:
        step = rng.choice([-2, -1, -1, 0, 1, 1, 2], p=[0.1, 0.25, 0.1, 0.1, 0.1, 0.25, 0.1])
        if rng.random() < 0.08:
            step = rng.integers(-5, 6)
        i = int(np.clip(i + step, 0, len(freqs) - 1))
        y = strike(freqs[i], decay * 1.8, parts, decay, amp=1.0, detune=rng.uniform(-0.002, 0.002))
        place(out, y, t, -0.45 + 0.9 * i / (len(freqs) - 1), rng.uniform(0.45, 1.0))
        if k % rng.integers(4, 9) == 0:
            b = strike(freqs[0] / 2 if rng.random() < 0.6 else freqs[min(len(freqs) - 1, 4)] / 2, 6.0,
                       [(1, 1.0, 1.0), (2, 0.2, 0.5)], 4.0, amp=0.35, attack_s=0.01)
            place(out, b, t, 0.0, 1.0)
        t += base * rng.choice([1, 1, 1, 1.5, 2, 3], p=[0.35, 0.2, 0.15, 0.1, 0.12, 0.08]) * rng.uniform(0.92, 1.08)
        k += 1
    out /= (np.abs(out).max() + 1e-9)
    return reverb(out, rng, decay_s=2.2, wet=0.35, tone_hz=4500)

def sc_bells(rng, n):
    T = n / SR
    out = np.zeros((n, 2), np.float32)
    f_base = rng.uniform(170, 400)
    ratios = [[1.0, 1.25, 1.5], [1.0, 1.2, 1.6], [1.0, 1.5], [1.0, 1.333, 1.5]][int(rng.integers(0, 4))]
    bells = [f_base * r for r in ratios]
    parts = [(0.5, 0.5, 1.5), (1, 1.0, 1.0), (1.2, 0.3, 0.8), (1.5, 0.4, 0.7), (2, 0.25, 0.5), (2.5, 0.15, 0.4), (3, 0.08, 0.3)]
    decay = rng.uniform(4, 8)
    for bi, f in enumerate(bells):
        mean_gap = rng.uniform(6, 16)
        for t in poisson_times(rng, T, lambda _: mean_gap, start=rng.uniform(3, 15)):
            y = strike(f, decay * 1.5, parts, decay, amp=1.0, attack_s=0.006)
            place(out, y, t, -0.5 + bi * 0.5, rng.uniform(0.5, 1.0))
            if rng.random() < 0.25:  # a second, quieter stroke
                place(out, y, t + rng.uniform(0.9, 1.8), -0.5 + bi * 0.5, rng.uniform(0.3, 0.6))
    out /= (np.abs(out).max() + 1e-9)
    out = np.stack([filt(sos_lp(1900, 2), out[:, 0]), filt(sos_lp(1900, 2), out[:, 1])], axis=1)
    w = filt(sos_bp(250, 900, 2), colored(rng, n, 0.0)) * (0.3 + 0.7 * walk(rng, n, 7))
    out += wide(w / (np.abs(w).max() + 1e-9), rng, 0.3) * 0.12
    return reverb(out, rng, decay_s=4.2, wet=0.55, tone_hz=2500)

def bird_note(rng, f0, kind, dur, vib_hz, vib_depth):
    m = int(dur * SR)
    tt = np.arange(m, dtype=np.float32) / SR
    if kind == 'rise':
        f = f0 * (1 + 0.35 * tt / dur)
    elif kind == 'fall':
        f = f0 * (1.35 - 0.35 * tt / dur)
    elif kind == 'arc':
        f = f0 * (1 + 0.3 * np.sin(np.pi * tt / dur))
    else:  # warble
        f = f0 * (1 + vib_depth * np.sin(2 * np.pi * vib_hz * tt))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph).astype(np.float32)
    a = max(1, int(0.012 * SR)); r = max(1, int(0.03 * SR))
    env = np.ones(m, np.float32); env[:a] = np.linspace(0, 1, a); env[-r:] *= np.linspace(1, 0, r)
    return y * env

def sc_birds(rng, n):
    T = n / SR
    out = np.zeros((n, 2), np.float32)
    for _ in range(rng.integers(3, 7)):
        f0 = rng.uniform(1900, 5200); pan = rng.uniform(-0.9, 0.9); lvl = rng.uniform(0.15, 0.5)
        motif = [(rng.choice(['rise', 'fall', 'arc', 'warble']), rng.uniform(0.06, 0.28), rng.uniform(0.8, 1.35))
                 for _ in range(rng.integers(2, 6))]
        vib = rng.uniform(15, 35); vd = rng.uniform(0.03, 0.08)
        t = rng.uniform(2, 12)
        while t < T - 2:
            tt = t
            for kind, dur, fm in motif:
                y = bird_note(rng, f0 * fm * rng.uniform(0.97, 1.03), kind, dur, vib, vd)
                place(out, y, tt, pan, lvl * rng.uniform(0.7, 1.0))
                tt += dur + rng.uniform(0.03, 0.12)
            t += rng.uniform(4, 15)
    out /= (np.abs(out).max() + 1e-9)
    out = np.stack([filt(sos_lp(5500, 2), out[:, 0]), filt(sos_lp(5500, 2), out[:, 1])], axis=1)
    air = filt(sos_bp(300, 2800, 2), colored(rng, n, 1.0)) * (0.4 + 0.6 * walk(rng, n, 9))
    out += wide(air / (np.abs(air).max() + 1e-9), rng, 0.3) * 0.12
    return reverb(out, rng, decay_s=1.4, wet=0.25, tone_hz=6000)

def sc_pad(rng, n):
    t = np.arange(n, dtype=np.float32) / SR
    T = n / SR
    root = rng.uniform(55, 110)
    name, freqs = scale_freqs(rng, root, octaves=2)
    picks = [freqs[0], freqs[0] * 2]
    picks += list(rng.choice(freqs[1:], size=3, replace=False))
    out = np.zeros((n, 2), np.float32)
    for i, f in enumerate(picks):
        d = rng.uniform(0.0025, 0.0045)
        v = (np.sin(2 * np.pi * f * (1 + d) * t) + np.sin(2 * np.pi * f * (1 - d) * t + 1.0)
             + 0.11 * np.sin(2 * np.pi * 3 * f * t) + 0.04 * np.sin(2 * np.pi * 5 * f * t)).astype(np.float32)
        v *= sines_env(rng, n, [rng.uniform(14, 35)], 0.15, 1.0)
        place(out, v, 0.0, rng.uniform(-0.6, 0.6), 1.0 / (1 + 0.5 * i))
    for ts in poisson_times(rng, T, lambda _: rng.uniform(20, 45), start=rng.uniform(10, 30)):
        f = rng.choice(freqs[len(freqs) // 2:])
        m = int(16 * SR); tt = np.arange(m, dtype=np.float32) / SR
        env = np.minimum(tt / 3.0, 1.0) * np.minimum(1.0, (16 - tt) / 5.0)
        v = (np.sin(2 * np.pi * f * 1.003 * tt) + np.sin(2 * np.pi * f * 0.997 * tt)).astype(np.float32) * env.astype(np.float32)
        place(out, v, ts, rng.uniform(-0.5, 0.5), 0.35)
    out = np.stack([filt(sos_lp(900, 2), out[:, 0]), filt(sos_lp(900, 2), out[:, 1])], axis=1)
    out /= (np.abs(out).max() + 1e-9)
    return reverb(out, rng, decay_s=3.6, wet=0.45, tone_hz=2200)

def sc_cave(rng, n):
    T = n / SR
    t = np.arange(n, dtype=np.float32) / SR
    out = np.zeros((n, 2), np.float32)
    name, freqs = scale_freqs(rng, rng.uniform(700, 1100), octaves=1)
    rate = rng.uniform(0.3, 1.2)
    for ts in poisson_times(rng, T, lambda _: 1.0 / rate):
        f = rng.choice(freqs)
        y = strike(f, 1.6, [(1, 1.0, 1.0), (2.5, 0.3, 0.5), (4.1, 0.1, 0.3)], rng.uniform(0.5, 1.1), amp=1.0, attack_s=0.002)
        place(out, y, ts, rng.uniform(-0.9, 0.9), rng.uniform(0.3, 1.0))
        if rng.random() < 0.2:
            place(out, y, ts + rng.uniform(0.12, 0.3), rng.uniform(-0.9, 0.9), rng.uniform(0.2, 0.5))
    out /= (np.abs(out).max() + 1e-9)
    drone = (np.sin(2 * np.pi * rng.uniform(52, 80) * t) + 0.3 * np.sin(2 * np.pi * rng.uniform(104, 160) * t)).astype(np.float32)
    drone *= sines_env(rng, n, [rng.uniform(20, 40)], 0.3, 1.0)
    out += wide(drone / (np.abs(drone).max() + 1e-9), rng, 0.1) * 0.12
    water = filt(sos_bp(100, 600, 2), colored(rng, n, 2.0)) * (0.4 + 0.6 * walk(rng, n, 1.2))
    out += wide(water / (np.abs(water).max() + 1e-9), rng, 0.3) * 0.1
    return reverb(out, rng, decay_s=4.8, wet=0.7, tone_hz=3000, predelay_s=0.04)

def sc_garden(rng, n):
    """A fresh performance of Jackson's eth-garden via the offline Web Audio renderer."""
    seconds = int(math.ceil(n / SR))
    seed = int(rng.integers(1, 2 ** 31 - 1))
    fd, tmp = tempfile.mkstemp(suffix='.wav', prefix='garden.'); os.close(fd)
    try:
        subprocess.run(['node', os.path.join(HERE, 'ethgarden-render.mjs'), str(seconds), str(seed), tmp],
                       check=True, capture_output=True, timeout=600, cwd=HERE)
        data, sr = sf.read(tmp, dtype='float32', always_2d=True)
    finally:
        try: os.remove(tmp)
        except OSError: pass
    if sr != SR:
        data = signal.resample_poly(data, SR, sr, axis=0).astype(np.float32)
    if data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    if len(data) < n:
        data = np.pad(data, ((0, n - len(data)), (0, 0)))
    return data[:n]

RENDER = {
    'rain': sc_rain, 'wind': sc_wind, 'stream': sc_stream, 'ocean': sc_ocean, 'chimes': sc_chimes,
    'bowl': sc_bowl, 'crickets': sc_crickets, 'fire': sc_fire, 'kalimba': sc_kalimba, 'bells': sc_bells,
    'birds': sc_birds, 'pad': sc_pad, 'cave': sc_cave, 'garden': sc_garden,
}

# ----------------------------------------------------------------------------- driver

def finish(x):
    """Level for hand-off: RMS at -20 dBFS, then a tanh soft clip so spiky scenes (fire
    crackles, drips) keep their peaks under 0 dBFS after ffmpeg raises the bed to -29 LUFS."""
    x = np.nan_to_num(x.astype(np.float32))
    x = np.stack([filt(sos_hp(28, 2), x[:, 0]), filt(sos_hp(28, 2), x[:, 1])], axis=1)
    rms = float(np.sqrt(np.mean(x ** 2))) + 1e-9
    x *= (10 ** (-20 / 20)) / rms
    x = np.tanh(x) * 0.95
    return x.astype(np.float32)

def pick(rng, avoid):
    pool = [s for s in SCENES if s not in avoid] or list(SCENES)
    return str(rng.choice(pool))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--pick', action='store_true', help='choose a scene and print scene|description|seed')
    ap.add_argument('--scene', default='random')
    ap.add_argument('--seconds', type=float, default=300)
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--avoid', default='', help='comma-separated scenes not to pick')
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    if a.list:
        for k, v in SCENES.items():
            print(f'{k:9s} {v}')
        return
    seed = a.seed if a.seed is not None else int.from_bytes(os.urandom(4), 'big')
    rng = np.random.default_rng(seed)
    avoid = {s.strip() for s in a.avoid.split(',') if s.strip()}
    scene = a.scene if a.scene != 'random' else pick(rng, avoid)
    if scene not in SCENES:
        sys.exit(f'unknown scene {scene!r}; try --list')
    if a.pick:
        print(f'{scene}|{SCENES[scene]}|{seed}')
        return
    if not a.out:
        sys.exit('--out required to render')
    n = int(a.seconds * SR)
    tried = []
    while True:
        try:
            x = RENDER[scene](rng, n)
            break
        except Exception as e:  # a scene failed (e.g. node missing): fall back to another
            print(f'scene {scene} failed: {e}', file=sys.stderr)
            tried.append(scene)
            rest = [s for s in SCENES if s not in avoid and s not in tried and s != 'garden']
            if not rest:
                sys.exit(1)
            scene = str(rng.choice(rest))
    sf.write(a.out, finish(x), SR, subtype='PCM_16')
    print(f'{scene}|{SCENES[scene]}|{seed}')

if __name__ == '__main__':
    main()
