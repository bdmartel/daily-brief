<?php session_start(); $authed = !empty($_SESSION['morning_auth']); ?>
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Morning Console</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#0b0e12;--panel:#12161d;--panel2:#161b24;--line:#232a36;--text:#e8e6e1;--muted:#8a9099;
--amber:#c96a3f;--amber2:#e8895a;--green:#5fae7f;--blue:#6ea3c7;--rose:#c77d9a;--gold:#c7a95f;}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:Inter,system-ui,sans-serif;min-height:100vh;padding-bottom:70px}
.mono{font-family:'JetBrains Mono',monospace}
header{padding:26px 18px 14px;max-width:660px;margin:0 auto}
h1{font-family:'JetBrains Mono',monospace;font-size:20px;letter-spacing:.18em;font-weight:700}
h1 .god{color:var(--amber2)}
.sub{color:var(--muted);font-size:12.5px;margin-top:5px;line-height:1.5}
#syncline{font-family:'JetBrains Mono',monospace;font-size:11px;margin-top:10px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.dot{width:8px;height:8px;border-radius:50%;background:var(--muted);display:inline-block}
.dot.ok{background:var(--green);box-shadow:0 0 8px rgba(95,174,127,.7)}
.dot.pending{background:var(--gold);box-shadow:0 0 8px rgba(199,169,95,.7)}
main{max-width:660px;margin:0 auto;padding:0 14px}
section{background:var(--panel);border:1px solid var(--line);border-radius:14px;margin:14px 0;overflow:hidden}
.sec-h{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid var(--line)}
.sec-h .tag{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.22em;color:var(--muted)}
.sec-h .emoji{font-size:16px}
.sec-b{padding:14px 16px}
.row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px dashed rgba(255,255,255,.05)}
.row:last-child{border-bottom:none}
.row label.big{font-size:14.5px;font-weight:500}
.hint{color:var(--muted);font-size:11.5px;margin-top:3px;line-height:1.45}
.switch{position:relative;width:46px;height:26px;flex:none}
.switch input{opacity:0;width:0;height:0}
.slider-t{position:absolute;inset:0;background:var(--line);border-radius:26px;transition:.18s;cursor:pointer}
.slider-t:before{content:"";position:absolute;width:20px;height:20px;left:3px;top:3px;background:#98a0ab;border-radius:50%;transition:.18s}
.switch input:checked + .slider-t{background:var(--amber)}
.switch input:checked + .slider-t:before{transform:translateX(20px);background:#fff2e2}
input[type=range]{width:150px;accent-color:var(--amber)}
select,input[type=text],textarea{background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:9px;padding:9px 11px;font-family:'JetBrains Mono',monospace;font-size:13px;width:100%}
textarea{min-height:74px;resize:vertical;line-height:1.55}
select{width:auto}
.val{font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--amber2);min-width:52px;text-align:right}
.btn{background:var(--panel2);border:1px solid var(--line);color:var(--text);border-radius:9px;padding:9px 14px;font-family:'JetBrains Mono',monospace;font-size:12.5px;cursor:pointer}
.btn.warn{background:#2a1712;border-color:#5a3325;color:#f0b9a0}
.btn.on{background:var(--amber);border-color:var(--amber2);color:#fff2e2}
.btn.small{padding:6px 10px;font-size:11.5px}
.btn:disabled{opacity:.45;cursor:default}
.chips{display:flex;gap:7px;flex-wrap:wrap;margin-top:9px}
.chip{font-family:'JetBrains Mono',monospace;font-size:11.5px;border:1px solid var(--line);border-radius:999px;padding:6px 11px;color:var(--muted);cursor:pointer;background:var(--panel2)}
.chip.on{color:#fff2e2;background:var(--amber);border-color:var(--amber2)}
.stack{padding:6px 0}
.stack .hint{margin-bottom:7px}
#savebar{position:fixed;bottom:0;left:0;right:0;background:rgba(11,14,18,.92);backdrop-filter:blur(8px);border-top:1px solid var(--line);padding:10px 16px;display:flex;justify-content:space-between;align-items:center;font-family:'JetBrains Mono',monospace;font-size:12px;z-index:9}
#savestate{color:var(--muted)}
#savestate.flash{color:var(--green)}
a{color:var(--blue)}
.login{max-width:340px;margin:24vh auto 0;text-align:center;padding:0 20px}
.login input{text-align:center;font-size:18px;letter-spacing:.4em;margin-top:16px}
.login .btn{margin-top:14px;width:100%}
details.lit summary{cursor:pointer;font-size:13.5px;font-weight:500;padding:9px 0;color:var(--muted)}
details.lit[open] summary{color:var(--text)}
/* hold */
#holdbanner{display:none;background:#2a1712;border:1px solid #5a3325;color:#f0b9a0;border-radius:12px;
  padding:11px 14px;margin:12px 0 0;font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.5}
body.held #holdbanner{display:block}
body.held section:not(#revisions){opacity:.55}
/* versions */
.vrow{display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px dashed rgba(255,255,255,.05);font-family:'JetBrains Mono',monospace;font-size:12.5px}
.vrow:last-child{border-bottom:none}
.vrow .vname{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.vrow .vdate{color:var(--muted);font-size:10.5px;flex:none}
.saveas{display:flex;gap:8px;margin-top:10px}
.saveas input{flex:1}
/* suggestions */
#sugbox{max-height:430px;overflow-y:auto;border:1px solid var(--line);border-radius:10px;background:var(--panel2)}
.sug{padding:11px 13px;border-bottom:1px dashed rgba(255,255,255,.06);display:flex;gap:10px;align-items:flex-start}
.sug:last-child{border-bottom:none}
.sug .s-main{flex:1;min-width:0}
.sug .s-t{font-size:13.5px;font-weight:600}
.sug .s-cat{font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:.14em;color:var(--gold);text-transform:uppercase}
.sug .s-b{color:var(--muted);font-size:11.5px;line-height:1.45;margin-top:2px}
/* preview */
.pv-card{border:1px solid var(--line);border-radius:11px;background:var(--panel2);padding:12px 13px;margin:10px 0}
.pv-card .pv-h{display:flex;justify-content:space-between;align-items:center;gap:8px}
.pv-card .pv-title{font-family:'JetBrains Mono',monospace;font-size:11.5px;letter-spacing:.16em;color:var(--muted)}
.pv-card .pv-conf{font-size:11.5px;color:var(--gold);margin-top:4px;font-family:'JetBrains Mono',monospace}
.pv-text{white-space:pre-wrap;font-size:14px;line-height:1.7;margin-top:10px;display:none}
.pv-note{color:var(--muted);font-size:10.5px;margin-top:7px;display:none;font-family:'JetBrains Mono',monospace}
.pv-btns{display:flex;gap:8px;flex:none}
#timeline{font-family:'JetBrains Mono',monospace;font-size:12px;line-height:2;color:var(--text);
  background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
#timeline .tl-t{color:var(--amber2)}
#timeline .off{color:var(--muted);text-decoration:line-through}
#toast{position:fixed;left:50%;transform:translateX(-50%);bottom:64px;background:#20262f;border:1px solid var(--line);
  color:var(--text);border-radius:10px;padding:10px 16px;font-family:'JetBrains Mono',monospace;font-size:12px;
  opacity:0;transition:.25s;pointer-events:none;z-index:10;max-width:88vw;text-align:center}
#toast.show{opacity:1}
</style>
</head>
<body>
<?php if (!$authed): ?>
<div class="login">
  <h1 class="mono">MORNING<span class="god"> CONSOLE</span></h1>
  <p class="sub">speak the word</p>
  <input id="pw" type="password" autocomplete="off" autofocus>
  <button class="btn" onclick="login()">enter</button>
  <p id="lerr" class="sub" style="color:#c96a3f"></p>
</div>
<script>
async function login(){
  const r = await fetch('api.php?fn=login',{method:'POST',body:JSON.stringify({pw:document.getElementById('pw').value})});
  if(r.ok) location.reload(); else document.getElementById('lerr').textContent='not the word';
}
document.getElementById('pw').addEventListener('keydown',e=>{if(e.key==='Enter')login()});
</script>
<?php else: ?>
<header>
  <h1>MORNING<span class="god"> CONSOLE</span></h1>
  <div class="sub">Every dial here is read by the Mac before dawn and shapes the next brief. You are the weather now.</div>
  <div id="syncline"><span class="dot" id="syncdot"></span><span id="synctext">reading the sky…</span></div>
  <div id="holdbanner">🔒 HELD — tomorrow runs exactly as configured. Dials, suggestions, and restores are locked until you release the hold.</div>
</header>
<main>

<section id="revisions"><!-- REVISIONS -->
  <div class="sec-h"><span class="emoji">🗿</span><span class="tag">REVISIONS — hold, save, restore</span></div>
  <div class="sec-b">
    <div class="row">
      <div><label class="big">Hold this revision</label><div class="hint">Freeze everything exactly as it is. Nothing — not even you, half-asleep — can change it until released.</div></div>
      <button class="btn" id="holdbtn"></button>
    </div>
    <div class="stack">
      <div class="hint">Save the current dials as a named version you can come back to. One-shots (whisper, doorway, wake hour, skip) aren't part of a version — they belong to a single morning.</div>
      <div class="saveas"><input type="text" id="vname" placeholder="name this morning… e.g. storm mode"><button class="btn" id="vsave">save</button></div>
    </div>
    <div id="vlist" style="margin-top:8px"></div>
  </div>
</section>

<section><!-- SUGGESTIONS -->
  <div class="sec-h"><span class="emoji">💡</span><span class="tag">SUGGESTIONS — scroll, tap, done</span></div>
  <div class="sec-b">
    <div class="chips" id="sugfilters" style="margin:0 0 10px"></div>
    <div id="sugbox"></div>
  </div>
</section>

<section><!-- PREVIEW -->
  <div class="sec-h"><span class="emoji">🔮</span><span class="tag">PREVIEW — tomorrow, as configured</span></div>
  <div class="sec-b">
    <div id="timeline"></div>
    <div class="hint" style="margin-top:8px">Previews below are generated fresh with the current revision in place — same recipe, same model, same voice. Live mornings will differ in the details (that's the point) but this is the shape and feel.</div>
    <div id="pvcards"></div>
  </div>
</section>

<section><!-- THE CLOCK -->
  <div class="sec-h"><span class="emoji">⏰</span><span class="tag">THE CLOCK — when the morning comes</span></div>
  <div class="sec-b">
    <div class="row">
      <div><label class="big">Alarm armed</label><div class="hint">Master switch. Off = the brief still builds silently, nothing plays.</div></div>
      <label class="switch"><input type="checkbox" id="alarm_enabled"><span class="slider-t"></span></label>
    </div>
    <div class="row">
      <div><label class="big">Let me sleep once</label><div class="hint" id="skiphint">One quiet morning, then back to normal.</div></div>
      <button class="btn warn" id="skipbtn"></button>
    </div>
    <div class="row">
      <div><label class="big">Wake hour <span class="hint" style="display:inline">(<span id="wakemorning">next morning</span> only)</span></label><div class="hint">One-time. The guard fires at this hour instead of 6, then forgets.</div></div>
      <select id="wake_hour">
        <option value="">6:00 (usual)</option>
        <option value="7">7:00</option><option value="8">8:00</option>
        <option value="9">9:00</option><option value="10">10:00</option>
      </select>
    </div>
    <div class="row">
      <div><label class="big">Loudness</label><div class="hint">Bedroom speaker volume when the morning begins.</div></div>
      <div style="display:flex;align-items:center;gap:10px"><input type="range" id="alarm_volume" min="30" max="100" step="5"><span class="val" id="vol_v"></span></div>
    </div>
  </div>
</section>

<section><!-- THE GARDEN -->
  <div class="sec-h"><span class="emoji">🌿</span><span class="tag">THE GARDEN — the sound before the words</span></div>
  <div class="sec-b">
    <div class="row">
      <div><label class="big">Garden overlay</label><div class="hint">Jackson's garden fades in first and hums under the voice.</div></div>
      <label class="switch"><input type="checkbox" id="garden_enabled"><span class="slider-t"></span></label>
    </div>
    <div class="row">
      <div><label class="big">Garden alone for</label><div class="hint">How long it plays solo before the first spoken word.</div></div>
      <div style="display:flex;align-items:center;gap:10px"><input type="range" id="garden_solo_seconds" min="0" max="300" step="30"><span class="val" id="solo_v"></span></div>
    </div>
  </div>
</section>

<section><!-- THE VOICE -->
  <div class="sec-h"><span class="emoji">🎙️</span><span class="tag">THE VOICE — how she sounds</span></div>
  <div class="sec-b">
    <div class="stack">
      <div class="hint">Voice weather: a standing direction layered onto her usual warmth. Blank = her natural self.</div>
      <input type="text" id="voice_weather" placeholder="e.g. hushed and slow, like it rained all night">
    </div>
    <div class="row" style="margin-top:6px">
      <div><label class="big">Your day (tasks)</label></div>
      <label class="switch"><input type="checkbox" id="tasks_enabled"><span class="slider-t"></span></label>
    </div>
    <div class="row">
      <div><label class="big">In touch (texts &amp; email)</label></div>
      <label class="switch"><input type="checkbox" id="comms_enabled"><span class="slider-t"></span></label>
    </div>
    <div class="row">
      <div><label class="big">At the mirror</label></div>
      <label class="switch"><input type="checkbox" id="mirror_enabled"><span class="slider-t"></span></label>
    </div>
  </div>
</section>

<section><!-- THE WORDS -->
  <div class="sec-h"><span class="emoji">🪶</span><span class="tag">THE WORDS — what tomorrow knows</span></div>
  <div class="sec-b">
    <div class="stack">
      <div class="hint">Whisper to tomorrow (<span id="whispermorning">next morning</span> only): leave a note tonight and the wake-up weaves its substance in — an appointment, a worry to set down, a thing to remember gently.</div>
      <textarea id="whisper" placeholder="e.g. Truck goes in at 9 — leave by 8:30. Go easy on me about the fence."></textarea>
    </div>
    <div class="row" style="margin-top:8px">
      <div><label class="big">Poem doorway</label><div class="hint">Where <span id="doorwaymorning">the next</span> poem enters. Auto rotates daily.</div></div>
      <select id="doorway">
        <option value="">auto (rotates)</option>
        <option value="sound">a sound</option>
        <option value="hands">something his hands know</option>
        <option value="animal">an animal mid-act</option>
        <option value="weather">weather in motion</option>
        <option value="object">an object where it was left</option>
        <option value="body">the body waking</option>
        <option value="halfmade">something half-finished</option>
        <option value="smell">a smell of the season</option>
      </select>
    </div>
  </div>
</section>

<section><!-- THE LITURGY -->
  <div class="sec-h"><span class="emoji">📜</span><span class="tag">THE LITURGY — the standing texts</span></div>
  <div class="sec-b">
    <details class="lit"><summary>Refrain (the poem's constant ending)</summary>
      <div class="stack"><div class="hint">Last line is spoken verbatim every morning; the lines above it are re-worded daily but keep this meaning. Blank = leave the Mac's current refrain alone.</div>
      <textarea id="refrain_text" placeholder="You don't have to be ready. You only have to be here.&#10;What you started is still becoming.&#10;So — up."></textarea></div>
    </details>
    <details class="lit"><summary>Fixed wake-up intro (override)</summary>
      <div class="stack"><div class="hint">Text here is read verbatim instead of a fresh intro. Type <b>auto</b> to clear an old override. Blank = no change.</div>
      <textarea id="intro_override" placeholder=""></textarea></div>
    </details>
    <details class="lit"><summary>Affirmation pool (one per line)</summary>
      <div class="stack"><div class="hint">The mirror moment draws 1–2 of these at random. Blank = leave the Mac's pool alone.</div>
      <textarea id="affirmations_text" style="min-height:110px"></textarea></div>
    </details>
  </div>
</section>

<div class="sub" style="padding:4px 4px 18px">The Mac drinks from this well every 2 minutes from 5:00 AM until the brief fires — late whispers still land. <a href="https://bdmartel.github.io/daily-brief/" target="_blank">today's brief →</a></div>
</main>

<div id="savebar"><span>⚡ autosaves</span><span id="savestate">—</span></div>
<div id="toast"></div>

<script>
const F = ['alarm_enabled','wake_hour','alarm_volume','garden_enabled','garden_solo_seconds','voice_weather',
           'whisper','doorway','tasks_enabled','comms_enabled','mirror_enabled','refrain_text','intro_override','affirmations_text'];
let S = null, V = [], saveTimer = null;
const $ = id => document.getElementById(id);

// ===================== SUGGESTIONS =====================
const SUGS = [
// voice weather
{c:'voice', t:'Soft rain', b:'Softer and slower, almost a whisper — for mornings that should start on tiptoe.', p:{voice_weather:'softer and slower, almost a whisper'}},
{c:'voice', t:'Sunrise', b:'Bright, quick, lightly teasing. She got there first and made the coffee.', p:{voice_weather:'bright, quick, lightly teasing'}},
{c:'voice', t:'Steady hand', b:'Low, even, reassuring — a hand on the shoulder before a heavy day.', p:{voice_weather:'low, steady, reassuring — like a hand on the shoulder'}},
{c:'voice', t:'Wry', b:'Amused, knowing — like she read your list and finds you charming anyway.', p:{voice_weather:"wry and amused, like she knows something you don't yet"}},
{c:'voice', t:'Dawn library', b:'As quiet as she can be while staying perfectly clear.', p:{voice_weather:'as quiet as possible while staying perfectly clear, like whispering in a library at dawn'}},
{c:'voice', t:'Campfire low', b:'Warm, unhurried, a little smoky — end-of-a-good-day energy at the start of one.', p:{voice_weather:'warm, unhurried, a little smoky, like talking low across a campfire'}},
{c:'voice', t:'Old friend on the porch', b:'Familiar, easy, zero performance. She\'s known you thirty years.', p:{voice_weather:'familiar and easy, like an old friend talking on a porch, no performance at all'}},
{c:'voice', t:'Pre-game coach', b:'Gentle but building — each sentence a notch more awake than the last.', p:{voice_weather:'gently building energy, each sentence slightly more awake and forward-leaning than the last'}},
{c:'voice', t:'Fog', b:'Slower, longer pauses, letting lines hang in the air.', p:{voice_weather:'slow, with long deliberate pauses, letting each line hang in the air like fog'}},
{c:'voice', t:'Espresso', b:'Crisp, clipped, efficient — for mornings with a train to catch.', p:{voice_weather:'crisp, quick and efficient, no lingering — a double espresso of a read'}},
{c:'voice', t:'Storyteller', b:'Leaning in, confiding, like the first page of a novel she loves.', p:{voice_weather:'leaning in and confiding, like reading the first page of a novel she loves'}},
{c:'voice', t:'Barely awake herself', b:'A little sleepy, warm, finding the words as she goes — waking up with you.', p:{voice_weather:'slightly sleepy and soft, like she just woke up too and is finding the words as she goes'}},
{c:'voice', t:'Smiling through it', b:'You can hear the smile the whole way through.', p:{voice_weather:'audibly smiling the whole way through'}},
{c:'voice', t:'Ranch hand', b:'Matter-of-fact, grounded, no fuss — the day\'s work is just the day\'s work.', p:{voice_weather:'matter-of-fact and grounded, like a ranch hand who has seen a thousand mornings'}},
{c:'voice', t:'Tender nurse', b:'Careful and kind, like changing a bandage — for bruised mornings.', p:{voice_weather:'extra careful and kind, tender without pity'}},
{c:'voice', t:'Natural (clear weather)', b:'Remove the direction — back to her usual warm self.', p:{voice_weather:''}},
// whispers
{c:'whisper', t:'Appointment anchor', b:'Template: the one thing with a clock on it. Edit the details after applying.', p:{whisper:'The truck goes in at 9 — leave by 8:30.', _stamp_whisper:true}},
{c:'whisper', t:'Go easy on me', b:'Tell tomorrow to be gentle about a specific thing.', p:{whisper:'Go easy on me about the fence — it will get done when it gets done.', _stamp_whisper:true}},
{c:'whisper', t:'Big day framing', b:'Name the day\'s one real event so the wake-up rises to it.', p:{whisper:'Today is the big planting day at Wilton — it matters to me. Frame the morning around it.', _stamp_whisper:true}},
{c:'whisper', t:'Gratitude seed', b:'Hand tomorrow something you\'re grateful for tonight; let it bloom at 6 AM.', p:{whisper:'Tonight I felt grateful for how the garden project is coming together. Remind me of that feeling.', _stamp_whisper:true}},
{c:'whisper', t:'Someone\'s birthday', b:'Never open the day forgetting it again.', p:{whisper:'It is ___\'s birthday today — make sure I don\'t let the morning pass without remembering.', _stamp_whisper:true}},
{c:'whisper', t:'Early departure', b:'For mornings when you need to be rolling fast.', p:{whisper:'I need to be out the door by 7 sharp — keep the morning moving.', _stamp_whisper:true}},
{c:'whisper', t:'Hard conversation ahead', b:'Let the wake-up steady you for it without naming it heavily.', p:{whisper:'I have a hard conversation today. Steady me — courage, softness, no dread.', _stamp_whisper:true}},
{c:'whisper', t:'Rest day permission', b:'Tomorrow\'s job is to convince you rest counts as work.', p:{whisper:'Tomorrow is a rest day on purpose. Give me full permission — no guilt, no list-energy.', _stamp_whisper:true}},
{c:'whisper', t:'Market day', b:'Wake up already pointed at the stand.', p:{whisper:'Market day — remind me what I love about selling what I grew.', _stamp_whisper:true}},
{c:'whisper', t:'Why I started', b:'Ask the morning to hand you back your own reasons.', p:{whisper:'Remind me why I started this farm — I need to hear it from the outside.', _stamp_whisper:true}},
{c:'whisper', t:'Weather warning', b:'Rain, heat, frost — let the wake-up fold the forecast into the plan.', p:{whisper:'Heavy rain is coming midday — nudge me to do outdoor work first.', _stamp_whisper:true}},
{c:'whisper', t:'Clear the whisper', b:'Tomorrow arrives with no note.', p:{whisper:'', _stamp_whisper:true}},
// poem doorways
{c:'poem', t:'Doorway: a sound', b:'Tomorrow\'s poem opens on something heard — near or far.', p:{doorway:'sound', _stamp_doorway:true}},
{c:'poem', t:'Doorway: the hands', b:'Opens on a texture, a tool, a latch — something your hands know blind.', p:{doorway:'hands', _stamp_doorway:true}},
{c:'poem', t:'Doorway: an animal', b:'Opens on a creature mid-act, doing exactly what it does.', p:{doorway:'animal', _stamp_doorway:true}},
{c:'poem', t:'Doorway: weather in motion', b:'Fog lifting, heat building, wind working the trees.', p:{doorway:'weather', _stamp_doorway:true}},
{c:'poem', t:'Doorway: the left object', b:'Opens on something sitting exactly where it was left.', p:{doorway:'object', _stamp_doorway:true}},
{c:'poem', t:'Doorway: the body', b:'Opens on breath, weight, warmth — feet finding the floor.', p:{doorway:'body', _stamp_doorway:true}},
{c:'poem', t:'Doorway: half-finished', b:'Opens on something outdoors caught mid-change.', p:{doorway:'halfmade', _stamp_doorway:true}},
{c:'poem', t:'Doorway: a smell', b:'Opens on a scent that belongs to this exact time of year.', p:{doorway:'smell', _stamp_doorway:true}},
{c:'poem', t:'Doorway: surprise me', b:'Back to the rotation — a different entrance every morning.', p:{doorway:'', _stamp_doorway:true}},
// clock & garden
{c:'clock', t:'Slow Sunday', b:'Quieter (55), garden alone a full 5 minutes. The day can wait.', p:{alarm_volume:55, garden_enabled:true, garden_solo_seconds:300}},
{c:'clock', t:'All business', b:'No garden, straight to the voice. Boots on.', p:{garden_enabled:false, garden_solo_seconds:0}},
{c:'clock', t:'Garden cathedral', b:'Five full minutes of the garden before a word is spoken.', p:{garden_enabled:true, garden_solo_seconds:300}},
{c:'clock', t:'Stealth morning', b:'Volume 40 — enough to surface you, not the whole house.', p:{alarm_volume:40}},
{c:'clock', t:'Full send', b:'Volume 85. You will not sleep through this.', p:{alarm_volume:85}},
{c:'clock', t:'Quick garden breath', b:'Just one minute of garden, then the day.', p:{garden_enabled:true, garden_solo_seconds:60}},
{c:'clock', t:'Sleep in — 7', b:'One-time: tomorrow fires at 7 instead of 6.', p:{wake_hour:7, _stamp_wake:true}},
{c:'clock', t:'Sleep in — 8', b:'One-time: tomorrow fires at 8.', p:{wake_hour:8, _stamp_wake:true}},
{c:'clock', t:'Back to 6', b:'Clear any one-time wake hour.', p:{wake_hour:null, _stamp_wake:true}},
{c:'clock', t:'Just the poem', b:'Garden + intro + poem, then silence. Tasks, texts and mirror stay off.', p:{tasks_enabled:false, comms_enabled:false, mirror_enabled:false}},
{c:'clock', t:'No-guilt morning', b:'Skip the task walk-through entirely — the list will keep.', p:{tasks_enabled:false}},
{c:'clock', t:'Hermit day', b:'No in-touch recap — yesterday\'s people can stay in yesterday.', p:{comms_enabled:false}},
{c:'clock', t:'Everything on', b:'All segments, garden, standard timing — the full liturgy.', p:{tasks_enabled:true, comms_enabled:true, mirror_enabled:true, garden_enabled:true, garden_solo_seconds:180, alarm_volume:70}},
// liturgy
{c:'liturgy', t:'Refrain: the original', b:'You don\'t have to be ready… what you started is still becoming. So — up.', p:{refrain_text:"You don't have to be ready. You only have to be here.\nWhat you started is still becoming.\nSo — up."}},
{c:'liturgy', t:'Refrain: hands version', b:'Same promise, felt through work: showing up is the whole job.', p:{refrain_text:"Nobody's asking you to be ready — just to put your hands on the day.\nEverything you've planted is still on its way up.\nSo — up."}},
{c:'liturgy', t:'Refrain: quiet version', b:'Smaller words, same meaning — for a hushed season.', p:{refrain_text:"You don't need to be ready. Here is enough.\nWhat you began is still growing toward you.\nSo — up."}},
{c:'liturgy', t:'Intro: plain and clean', b:'Fixed override — six calm words and into the poem.', p:{intro_override:'Good morning, Ben. No hurry at all. Here comes the poem.'}},
{c:'liturgy', t:'Intro: back to fresh', b:'Clear any fixed intro — a new one gets written every morning.', p:{intro_override:'auto'}},
{c:'liturgy', t:'Add: water line', b:'Appends the Bruce Lee water line to the affirmation pool.', p:{__append_aff:'I move like water — I adapt, I keep flowing, I find the way around.'}},
{c:'liturgy', t:'Add: the address', b:'Appends "I am the address — I don\'t need to land anywhere else to be home."', p:{__append_aff:"I am the address — I don't need to land anywhere else to be home."}},
{c:'liturgy', t:'Add: hands on today', b:'Appends "I release what I can\'t control and put my hands on what I can."', p:{__append_aff:"I release what I can't control and put my hands on what I can."}},
// full recipes
{c:'recipe', t:'Storm Morning', b:'Soft-rain voice, 4 min of garden, volume 60, poem enters through weather.', p:{voice_weather:'softer and slower, almost a whisper', garden_solo_seconds:240, alarm_volume:60, doorway:'weather', _stamp_doorway:true}},
{c:'recipe', t:'Race Day', b:'Espresso voice, 1 min garden, volume 80 — up and out.', p:{voice_weather:'crisp, quick and efficient, no lingering — a double espresso of a read', garden_solo_seconds:60, alarm_volume:80}},
{c:'recipe', t:'Sabbath', b:'Steady-hand voice, 5 min garden, no tasks, no in-touch. Just poem and mirror.', p:{voice_weather:'low, steady, reassuring — like a hand on the shoulder', garden_solo_seconds:300, tasks_enabled:false, comms_enabled:false, mirror_enabled:true}},
{c:'recipe', t:'Deep Field', b:'Garden-forward and hermit: 5 min solo, no in-touch, ranch-hand voice.', p:{garden_solo_seconds:300, comms_enabled:false, voice_weather:'matter-of-fact and grounded, like a ranch hand who has seen a thousand mornings'}},
{c:'recipe', t:'Open Hands', b:'Mirror-centered morning: no tasks, no comms, tender voice, body doorway.', p:{tasks_enabled:false, comms_enabled:false, mirror_enabled:true, voice_weather:'extra careful and kind, tender without pity', doorway:'body', _stamp_doorway:true}},
{c:'recipe', t:'Winter Light', b:'Dawn-library voice, long garden, smell doorway — hushed and holy.', p:{voice_weather:'as quiet as possible while staying perfectly clear, like whispering in a library at dawn', garden_solo_seconds:300, alarm_volume:55, doorway:'smell', _stamp_doorway:true}},
{c:'recipe', t:'Homecoming', b:'Old-friend voice, everything on, hands doorway — a morning that knows you.', p:{voice_weather:'familiar and easy, like an old friend talking on a porch, no performance at all', tasks_enabled:true, comms_enabled:true, mirror_enabled:true, doorway:'hands', _stamp_doorway:true}},
{c:'recipe', t:'Plain Bread', b:'Factory settings — the morning exactly as first built.', p:{voice_weather:'', garden_enabled:true, garden_solo_seconds:180, alarm_volume:70, tasks_enabled:true, comms_enabled:true, mirror_enabled:true}},
];
const CATS = [['all','all'],['recipe','recipes'],['voice','voice'],['whisper','whispers'],['poem','poem'],['clock','clock & garden'],['liturgy','liturgy']];
let sugCat = 'all';

function renderSugs(){
  $('sugfilters').innerHTML = CATS.map(([k,l]) => `<span class="chip ${sugCat===k?'on':''}" data-c="${k}">${l}</span>`).join('');
  $('sugfilters').querySelectorAll('.chip').forEach(c => c.onclick = () => { sugCat=c.dataset.c; renderSugs(); });
  const items = SUGS.filter(s => sugCat==='all' || s.c===sugCat);
  $('sugbox').innerHTML = items.map((s,i) => `<div class="sug"><div class="s-main"><div class="s-cat">${s.c}</div><div class="s-t">${s.t}</div><div class="s-b">${s.b}</div></div><div class="pv-btns"><button class="btn small" data-i="${SUGS.indexOf(s)}">apply</button></div></div>`).join('');
  $('sugbox').querySelectorAll('button').forEach(b => b.onclick = () => applySug(SUGS[+b.dataset.i]));
}
async function applySug(s){
  const p = Object.assign({}, s.p);
  if (p.__append_aff){
    const cur = ($('affirmations_text').value || '').trimEnd();
    p.affirmations_text = cur ? cur + '\n' + p.__append_aff : p.__append_aff;
    delete p.__append_aff;
  }
  await save(p, true);
  toast('applied: ' + s.t);
}

// ===================== PREVIEW =====================
const PV_SECTIONS = [
  {id:'intro',  title:'WAKE-UP', gen:true,  conf: s => (s.intro_override && s.intro_override!=='auto') ? 'fixed override' :
      ('fresh each morning' + (s.whisper && s.whisper_date===s.next_morning ? ' · whisper woven in' : ''))},
  {id:'poem',   title:'POEM', gen:true, conf: s => 'doorway: ' + (s.doorway && s.doorway_date===s.next_morning ? $('doorway').options[$('doorway').selectedIndex].text : 'auto rotation') },
  {id:'tasks',  title:'YOUR DAY', gen:false, conf: s => s.tasks_enabled ? 'on — assembled live at 6 AM from your task list: real finishes praised once, lingering items nudged honestly, deleted things never spoken' : 'off — no task talk tomorrow'},
  {id:'comms',  title:'IN TOUCH', gen:false, conf: s => s.comms_enabled ? 'on — synthesized at 6 AM from your sent texts + active email threads; no numbers, no quotes, no invented names' : 'off — yesterday\'s people stay in yesterday'},
  {id:'mirror', title:'AT THE MIRROR', gen:true, conf: s => s.mirror_enabled ? 'on — 1–2 affirmations drawn from the pool and coached into' : 'off'},
];
let pvAudio = null;

function renderTimeline(){
  const wk = (S.wake_date===S.next_morning && S.wake_hour) ? S.wake_hour + ':00' : '6:00';
  const skip = S.skip_date && S.skip_date >= S.next_morning;
  const solo = S.garden_solo_seconds;
  const mins = Math.floor(solo/60), secs = solo%60;
  const soloTxt = solo ? `${mins}${secs? ':'+String(secs).padStart(2,'0') : ''} min` : 'no time';
  let out = '';
  if (!S.alarm_enabled) out += `<div>🔕 alarm disarmed — the brief builds silently, nothing plays</div>`;
  else if (skip) out += `<div>😴 skipping ${new Date(S.skip_date+'T06:00:00').toLocaleDateString([], {weekday:'long'})} — one quiet morning</div>`;
  else {
    out += `<div><span class="tl-t">${wk}</span> — volume to ${S.alarm_volume}, bedroom speaker, brief opens</div>`;
    out += S.garden_enabled ? `<div><span class="tl-t">＋0:00</span> — garden fades in, alone for ${soloTxt}</div>` : `<div class="off">garden overlay off</div>`;
    out += `<div><span class="tl-t">＋${solo && S.garden_enabled ? soloTxt : '0:00'}</span> — wake-up intro${S.whisper && S.whisper_date===S.next_morning ? ' (your whisper woven in)' : ''}, then the poem</div>`;
    out += `<div class="${S.tasks_enabled?'':'off'}">→ your day${S.tasks_enabled?'':' (off)'}</div>`;
    out += `<div class="${S.comms_enabled?'':'off'}">→ in touch${S.comms_enabled?'':' (off)'}</div>`;
    out += `<div class="${S.mirror_enabled?'':'off'}">→ at the mirror${S.mirror_enabled?'':' (off)'}</div>`;
    if (S.garden_enabled) out += `<div>→ garden fades itself out by 6:30 in</div>`;
  }
  if (S.voice_weather) out += `<div>🎙 voice weather: “${S.voice_weather}”</div>`;
  $('timeline').innerHTML = out;
}

function renderPvCards(){
  $('pvcards').innerHTML = PV_SECTIONS.map(p => `
    <div class="pv-card" id="pv-${p.id}">
      <div class="pv-h"><div><div class="pv-title">${p.title}</div><div class="pv-conf">${p.conf(S)}</div></div>
      <div class="pv-btns">${p.gen ? `<button class="btn small" data-g="${p.id}">✨ preview</button><button class="btn small" data-h="${p.id}" style="display:none">▶ hear it</button>` : ''}</div></div>
      <div class="pv-text" id="pvt-${p.id}"></div><div class="pv-note" id="pvn-${p.id}"></div>
    </div>`).join('');
  $('pvcards').querySelectorAll('[data-g]').forEach(b => b.onclick = () => genPreview(b.dataset.g, b));
  $('pvcards').querySelectorAll('[data-h]').forEach(b => b.onclick = () => hearPreview(b.dataset.h, b));
}
async function genPreview(id, btn){
  btn.disabled = true; btn.textContent = '…conjuring';
  try {
    const r = await fetch('api.php?fn=preview', {method:'POST', body: JSON.stringify({section:id})});
    const d = await r.json();
    if (d.error) { toast(d.error); return; }
    const t = $('pvt-'+id); t.textContent = d.text; t.style.display = 'block';
    if (d.note) { const n = $('pvn-'+id); n.textContent = '※ ' + d.note; n.style.display = 'block'; }
    const hb = document.querySelector(`[data-h="${id}"]`); if (hb) hb.style.display = '';
  } catch(e){ toast('preview failed'); }
  finally { btn.disabled = false; btn.textContent = '✨ preview'; }
}
async function hearPreview(id, btn){
  const text = $('pvt-'+id).textContent;
  if (!text) return;
  if (pvAudio) { pvAudio.pause(); pvAudio = null; }
  btn.disabled = true; btn.textContent = '…rendering';
  try {
    const r = await fetch('api.php?fn=preview_tts', {method:'POST', body: JSON.stringify({text})});
    const d = await r.json();
    if (d.error) { toast(d.error); return; }
    pvAudio = new Audio('data:audio/mp3;base64,' + d.audio);
    pvAudio.play();
  } catch(e){ toast('tts failed'); }
  finally { btn.disabled = false; btn.textContent = '▶ hear it'; }
}

// ===================== VERSIONS / HOLD =====================
function renderVersions(){
  const rows = [`<div class="vrow"><span class="vname">🪨 Original (as first built)</span><span class="vdate">factory</span><button class="btn small" data-r="original">restore</button></div>`]
    .concat(V.map(v => `<div class="vrow"><span class="vname">${escapeHtml(v.name)}</span><span class="vdate">${new Date(v.created).toLocaleDateString([], {month:'short',day:'numeric'})}</span><button class="btn small" data-r="${v.id}">restore</button><button class="btn small warn" data-d="${v.id}">×</button></div>`));
  $('vlist').innerHTML = rows.join('');
  $('vlist').querySelectorAll('[data-r]').forEach(b => b.onclick = () => restoreVersion(b.dataset.r));
  $('vlist').querySelectorAll('[data-d]').forEach(b => b.onclick = () => deleteVersion(b.dataset.d));
}
function escapeHtml(s){ const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
async function loadVersions(){
  const r = await fetch('api.php?fn=versions');
  if (r.ok) { V = (await r.json()).versions || []; renderVersions(); }
}
async function saveVersion(){
  const name = $('vname').value.trim();
  if (!name) { toast('give it a name'); return; }
  const r = await fetch('api.php?fn=save_version', {method:'POST', body: JSON.stringify({name})});
  if (r.ok) { V = (await r.json()).versions; renderVersions(); $('vname').value=''; toast('saved: ' + name); }
}
async function restoreVersion(id){
  const r = await fetch('api.php?fn=restore_version', {method:'POST', body: JSON.stringify({id})});
  if (r.status === 423) { toast('🔒 held — release the hold first'); return; }
  if (r.ok) { S = await r.json(); render(); toast(id==='original' ? 'restored to original' : 'version restored'); }
}
async function deleteVersion(id){
  const r = await fetch('api.php?fn=delete_version', {method:'POST', body: JSON.stringify({id})});
  if (r.ok) { V = (await r.json()).versions; renderVersions(); toast('version deleted'); }
}
function renderHold(){
  document.body.classList.toggle('held', !!S.hold);
  $('holdbtn').textContent = S.hold ? '🔒 held — release' : '🔓 hold';
  $('holdbtn').className = S.hold ? 'btn on' : 'btn';
}
async function toggleHold(){
  await save(S.hold ? {_unhold:true} : {_hold:true}, true);
  toast(S.hold ? '🔒 revision held' : 'hold released');
}

// ===================== CORE =====================
function toast(m){ const t=$('toast'); t.textContent=m; t.classList.add('show'); clearTimeout(t._h); t._h=setTimeout(()=>t.classList.remove('show'),2600); }
function fmtTime(iso){ if(!iso) return null; const d=new Date(iso);
  return d.toLocaleString([], {month:'short', day:'numeric', hour:'numeric', minute:'2-digit'}); }

function renderSync(){
  const dot=$('syncdot'), t=$('synctext');
  const upd = S.updated_at ? new Date(S.updated_at) : null;
  const sync = S.mac_last_sync ? new Date(S.mac_last_sync) : null;
  if (upd && (!sync || sync < upd)) { dot.className='dot pending'; t.textContent='MAC LINK: change pending — lands at the pre-dawn sync (from 5:00 AM)'; }
  else if (sync) { dot.className='dot ok'; t.textContent='MAC LINK: last drank ' + fmtTime(S.mac_last_sync) + (S.mac_last_run ? ' · last morning ran ' + fmtTime(S.mac_last_run) : ''); }
  else { dot.className='dot'; t.textContent='MAC LINK: not yet synced'; }
}

function render(){
  for (const k of ['alarm_enabled','garden_enabled','tasks_enabled','comms_enabled','mirror_enabled']) $(k).checked = !!S[k];
  $('wake_hour').value = S.wake_date === S.next_morning && S.wake_hour ? String(S.wake_hour) : '';
  $('alarm_volume').value = S.alarm_volume; $('vol_v').textContent = S.alarm_volume;
  $('garden_solo_seconds').value = S.garden_solo_seconds;
  $('solo_v').textContent = (S.garden_solo_seconds/60).toFixed(1).replace('.0','') + ' min';
  $('voice_weather').value = S.voice_weather || '';
  $('whisper').value = S.whisper_date === S.next_morning ? (S.whisper||'') : '';
  $('doorway').value = S.doorway_date === S.next_morning ? (S.doorway||'') : '';
  for (const k of ['refrain_text','intro_override','affirmations_text']) $(k).value = S[k] || '';
  const nm = new Date(S.next_morning + 'T06:00:00').toLocaleDateString([], {weekday:'long'});
  for (const id of ['wakemorning','whispermorning','doorwaymorning']) $(id).textContent = nm;
  renderSkip(); renderSync(); renderHold(); renderTimeline(); renderPvCards();
}
function renderSkip(){
  const on = S.skip_date && S.skip_date >= S.next_morning;
  $('skipbtn').textContent = on ? 'sleeping ✓ (undo)' : 'skip next morning';
  $('skipbtn').className = on ? 'btn on' : 'btn warn';
  $('skiphint').textContent = on ? ('The ' + new Date(S.skip_date+'T06:00:00').toLocaleDateString([], {weekday:'long'}) + ' alarm stays quiet. Tap to undo.') : 'One quiet morning, then back to normal.';
}

function collect(){
  const b = {};
  for (const k of ['alarm_enabled','garden_enabled','tasks_enabled','comms_enabled','mirror_enabled']) b[k] = $(k).checked;
  b.alarm_volume = +$('alarm_volume').value;
  b.garden_solo_seconds = +$('garden_solo_seconds').value;
  b.voice_weather = $('voice_weather').value.trim();
  b.whisper = $('whisper').value.trim(); b._stamp_whisper = true;
  b.doorway = $('doorway').value; b._stamp_doorway = true;
  b.wake_hour = $('wake_hour').value ? +$('wake_hour').value : null; b._stamp_wake = true;
  for (const k of ['refrain_text','intro_override','affirmations_text']) b[k] = $(k).value;
  return b;
}

async function save(extra, extraOnly){
  const body = extraOnly ? (extra || {}) : Object.assign(collect(), extra || {});
  $('savestate').textContent = 'committing…'; $('savestate').className='';
  const r = await fetch('api.php?fn=save', {method:'POST', body: JSON.stringify(body)});
  if (r.status === 423) { $('savestate').textContent='🔒 held'; toast('🔒 held — release the hold to change anything'); const rs = await fetch('api.php?fn=state'); if (rs.ok){ S = await rs.json(); render(); } return; }
  if (r.ok) { S = await r.json(); render();
    $('savestate').textContent = 'COMMITTED ✓ ' + new Date().toLocaleTimeString([], {hour:'numeric',minute:'2-digit'});
    $('savestate').className = 'flash';
  } else { $('savestate').textContent = 'save failed'; toast('save failed'); }
}
function queueSave(){ clearTimeout(saveTimer); saveTimer = setTimeout(()=>save(), 700); }

async function boot(){
  const r = await fetch('api.php?fn=state');
  if (r.status === 401) { location.reload(); return; }
  S = await r.json(); render(); renderSugs(); loadVersions();
  for (const k of F) { const el=$(k); el.addEventListener(el.tagName==='SELECT'||el.type==='checkbox'?'change':'input', () => {
    if (k==='alarm_volume') $('vol_v').textContent = el.value;
    if (k==='garden_solo_seconds') $('solo_v').textContent = (el.value/60).toFixed(1).replace('.0','') + ' min';
    queueSave();
  }); }
  $('skipbtn').addEventListener('click', () => save(S.skip_date && S.skip_date >= S.next_morning ? {_unskip:true} : {_skip_next:true}, true));
  $('holdbtn').addEventListener('click', toggleHold);
  $('vsave').addEventListener('click', saveVersion);
  setInterval(async () => { const r2 = await fetch('api.php?fn=state'); if (r2.ok) { const fresh = await r2.json();
    S.mac_last_sync = fresh.mac_last_sync; S.mac_last_run = fresh.mac_last_run; renderSync(); } }, 60000);
}
boot();
</script>
<?php endif; ?>
</body>
</html>
