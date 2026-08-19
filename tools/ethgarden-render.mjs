// Offline render of the eth-garden.vercel.app ambient audio engine.
// Faithful port of the synthesis code from the site's JS bundle (used with
// Jackson's permission). The browser engine schedules notes with setTimeout;
// here every event time is pre-computed so an OfflineAudioContext can render
// the identical signal chain deterministically.
//
// Usage: node ethgarden-render.mjs <seconds> <seed> <out.wav>
import { OfflineAudioContext } from 'node-web-audio-api';
import { writeFileSync } from 'node:fs';

const DURATION = parseFloat(process.argv[2] ?? '390');
const SEED = parseInt(process.argv[3] ?? '20260818', 10);
const OUT = process.argv[4] ?? 'ethgarden.wav';
const SR = 44100;

// mulberry32 — deterministic stand-in for Math.random()
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rand = mulberry32(SEED);

// === Engine constants (verbatim from the bundle) ===
const CONFIG = { masterVolume: 0.14, reverbWet: 0.9, reverbDry: 0.7 };
const mtof = (m) => 440 * 2 ** ((m - 69) / 12);
const POOL_LOW  = [57, 59, 61, 64, 66];  // pads, lower voice
const POOL_MID  = [66, 69, 71, 73, 76];  // pads, upper voice
const POOL_HIGH = [78, 81, 83, 85, 88];  // chimes
const DRONE    = [45, 52];               // A2, E3
const pick = (arr) => arr[(rand() * arr.length) | 0];

const ctx = new OfflineAudioContext(2, Math.floor(DURATION * SR), SR);

// === Master chain: gain -> lowpass 2200 -> destination ===
const master = ctx.createGain();
master.gain.value = 0;
const masterLP = ctx.createBiquadFilter();
masterLP.type = 'lowpass';
masterLP.frequency.value = 2200;
master.connect(masterLP);
masterLP.connect(ctx.destination);
master.gain.linearRampToValueAtTime(CONFIG.masterVolume, 5);

// === Reverb: 3.2s decaying-noise impulse, wet/dry into master ===
function impulse(seconds, decayPow) {
  const len = Math.floor(seconds * SR);
  const buf = ctx.createBuffer(2, len, SR);
  for (let ch = 0; ch < 2; ch++) {
    const d = buf.getChannelData(ch);
    for (let i = 0; i < len; i++) d[i] = (rand() * 2 - 1) * (1 - i / len) ** decayPow;
  }
  return buf;
}
const convolver = ctx.createConvolver();
convolver.buffer = impulse(3.2, 2.4);
const wet = ctx.createGain();
wet.gain.value = CONFIG.reverbWet;
convolver.connect(wet);
wet.connect(master);
const dry = ctx.createGain();
dry.gain.value = CONFIG.reverbDry;
dry.connect(master);
const toBus = (node) => { node.connect(dry); node.connect(convolver); };

// === Drone: A2 + E3, sine + triangle (+7c, slow LFO wobble), LP 480 ===
for (const midi of DRONE) {
  const f = mtof(midi);
  const g = ctx.createGain();
  g.gain.value = 0;
  const lp = ctx.createBiquadFilter();
  lp.type = 'lowpass';
  lp.frequency.value = 480;
  const oscA = ctx.createOscillator();
  oscA.type = 'sine'; oscA.frequency.value = f;
  const oscB = ctx.createOscillator();
  oscB.type = 'triangle'; oscB.frequency.value = f; oscB.detune.value = 7;
  oscA.connect(g); oscB.connect(g); g.connect(lp); toBus(lp);
  const lfo = ctx.createOscillator();
  lfo.frequency.value = 0.04 + rand() * 0.05;
  const lfoAmt = ctx.createGain();
  lfoAmt.gain.value = 5;
  lfo.connect(lfoAmt); lfoAmt.connect(oscB.detune);
  oscA.start(); oscB.start(); lfo.start();
  g.gain.linearRampToValueAtTime(0.06, 8);
}

// === Pad voice (site's HB): two ±5c sines, LP 1100 Q .4, slow swell ===
function pad(now, midi, sustain) {
  const f = mtof(midi);
  const g = ctx.createGain();
  g.gain.value = 0;
  const lp = ctx.createBiquadFilter();
  lp.type = 'lowpass'; lp.frequency.value = 1100; lp.Q.value = 0.4;
  const pan = ctx.createStereoPanner();
  pan.pan.value = (rand() * 2 - 1) * 0.6;
  const oscs = [];
  for (const cents of [-5, 5]) {
    const o = ctx.createOscillator();
    o.type = 'sine'; o.frequency.value = f; o.detune.value = cents;
    o.connect(g); oscs.push(o);
  }
  g.connect(lp); lp.connect(pan); toBus(pan);
  const atk = 2.6, rel = 3.5, lvl = 0.13;
  g.gain.setValueAtTime(0, now);
  g.gain.linearRampToValueAtTime(lvl, now + atk);
  g.gain.setValueAtTime(lvl, now + atk + sustain);
  g.gain.linearRampToValueAtTime(1e-4, now + atk + sustain + rel);
  const end = now + atk + sustain + rel + 0.1;
  oscs.forEach((o) => { o.start(now); o.stop(end); });
}

// === Chime voice (site's fae): sine + 2.01x partial, fast pluck ===
function chime(now, midi) {
  const f = mtof(midi);
  const g = ctx.createGain();
  g.gain.value = 0;
  const pan = ctx.createStereoPanner();
  pan.pan.value = (rand() * 2 - 1) * 0.7;
  const oscA = ctx.createOscillator();
  oscA.type = 'sine'; oscA.frequency.value = f;
  const oscB = ctx.createOscillator();
  oscB.type = 'sine'; oscB.frequency.value = f * 2.01;
  const partial = ctx.createGain();
  partial.gain.value = 0.3;
  oscB.connect(partial); partial.connect(g); oscA.connect(g);
  g.connect(pan); toBus(pan);
  const dur = 4.5;
  g.gain.setValueAtTime(0, now);
  g.gain.linearRampToValueAtTime(0.11, now + 0.02);
  g.gain.exponentialRampToValueAtTime(1e-4, now + dur);
  oscA.start(now); oscB.start(now);
  oscA.stop(now + dur + 0.1); oscB.stop(now + dur + 0.1);
}

// === Schedulers: same distributions as the site's setTimeout loops ===
let padCount = 0, chimeCount = 0;
for (let t = 0.8; t < DURATION; t += 5 + rand() * 5) {
  pad(t, pick(POOL_LOW), 2 + rand() * 3); padCount++;
  if (rand() < 0.8) { pad(t, pick(POOL_MID), 2 + rand() * 3); padCount++; }
}
for (let t = 6; t < DURATION; t += 9 + rand() * 12) {
  if (rand() < 0.75) { chime(t, pick(POOL_HIGH)); chimeCount++; }
}
console.log(`events: ${padCount} pads, ${chimeCount} chimes over ${DURATION}s (seed ${SEED})`);

// === Render and write 16-bit stereo WAV ===
const rendered = await ctx.startRendering();
const n = rendered.length;
const pcm = new Int16Array(n * 2);
const L = rendered.getChannelData(0), R = rendered.getChannelData(1);
let peak = 0;
for (let i = 0; i < n; i++) {
  const l = Math.max(-1, Math.min(1, L[i])), r = Math.max(-1, Math.min(1, R[i]));
  peak = Math.max(peak, Math.abs(l), Math.abs(r));
  pcm[i * 2] = l * 32767; pcm[i * 2 + 1] = r * 32767;
}
const dataSize = pcm.length * 2;
const header = Buffer.alloc(44);
header.write('RIFF', 0); header.writeUInt32LE(36 + dataSize, 4); header.write('WAVE', 8);
header.write('fmt ', 12); header.writeUInt32LE(16, 16); header.writeUInt16LE(1, 20);
header.writeUInt16LE(2, 22); header.writeUInt32LE(SR, 24); header.writeUInt32LE(SR * 4, 28);
header.writeUInt16LE(4, 32); header.writeUInt16LE(16, 34);
header.write('data', 36); header.writeUInt32LE(dataSize, 40);
writeFileSync(OUT, Buffer.concat([header, Buffer.from(pcm.buffer)]));
console.log(`wrote ${OUT} (${(dataSize / 1048576).toFixed(1)} MB, peak ${peak.toFixed(3)})`);
