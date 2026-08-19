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
.chips{display:flex;gap:7px;flex-wrap:wrap;margin-top:9px}
.chip{font-family:'JetBrains Mono',monospace;font-size:11.5px;border:1px solid var(--line);border-radius:999px;padding:6px 11px;color:var(--muted);cursor:pointer;background:var(--panel2)}
.chip.on{color:#fff2e2;background:var(--amber);border-color:var(--amber2)}
.stack{padding:6px 0}
.stack .hint{margin-bottom:7px}
#savebar{position:fixed;bottom:0;left:0;right:0;background:rgba(11,14,18,.92);backdrop-filter:blur(8px);border-top:1px solid var(--line);padding:10px 16px;display:flex;justify-content:space-between;align-items:center;font-family:'JetBrains Mono',monospace;font-size:12px}
#savestate{color:var(--muted)}
#savestate.flash{color:var(--green)}
a{color:var(--blue)}
.login{max-width:340px;margin:24vh auto 0;text-align:center;padding:0 20px}
.login input{text-align:center;font-size:18px;letter-spacing:.4em;margin-top:16px}
.login .btn{margin-top:14px;width:100%}
details.lit summary{cursor:pointer;font-size:13.5px;font-weight:500;padding:9px 0;color:var(--muted)}
details.lit[open] summary{color:var(--text)}
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
</header>
<main>

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
      <div class="chips" id="weatherchips">
        <span class="chip" data-w="">natural</span>
        <span class="chip" data-w="softer and slower, almost a whisper">soft rain</span>
        <span class="chip" data-w="bright, quick, lightly teasing">sunrise</span>
        <span class="chip" data-w="low, steady, reassuring — like a hand on the shoulder">steady hand</span>
        <span class="chip" data-w="wry and amused, like she knows something you don't yet">wry</span>
      </div>
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

<script>
const F = ['alarm_enabled','wake_hour','alarm_volume','garden_enabled','garden_solo_seconds','voice_weather',
           'whisper','doorway','tasks_enabled','comms_enabled','mirror_enabled','refrain_text','intro_override','affirmations_text'];
let S = null, saveTimer = null;
const $ = id => document.getElementById(id);

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
  document.querySelectorAll('#weatherchips .chip').forEach(c => c.classList.toggle('on', c.dataset.w === (S.voice_weather||'')));
  renderSkip(); renderSync();
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

async function save(extra){
  const body = Object.assign(collect(), extra || {});
  $('savestate').textContent = 'committing…'; $('savestate').className='';
  const r = await fetch('api.php?fn=save', {method:'POST', body: JSON.stringify(body)});
  if (r.ok) { S = await r.json(); render();
    $('savestate').textContent = 'COMMITTED ✓ ' + new Date().toLocaleTimeString([], {hour:'numeric',minute:'2-digit'});
    $('savestate').className = 'flash';
  } else { $('savestate').textContent = 'save failed — retrying'; setTimeout(()=>save(extra), 2500); }
}
function queueSave(){ clearTimeout(saveTimer); saveTimer = setTimeout(()=>save(), 700); }

async function boot(){
  const r = await fetch('api.php?fn=state');
  if (r.status === 401) { location.reload(); return; }
  S = await r.json(); render();
  for (const k of F) { const el=$(k); el.addEventListener(el.tagName==='SELECT'||el.type==='checkbox'?'change':'input', () => {
    if (k==='alarm_volume') $('vol_v').textContent = el.value;
    if (k==='garden_solo_seconds') $('solo_v').textContent = (el.value/60).toFixed(1).replace('.0','') + ' min';
    queueSave();
  }); }
  $('skipbtn').addEventListener('click', () => save(S.skip_date && S.skip_date >= S.next_morning ? {_unskip:true} : {_skip_next:true}));
  document.querySelectorAll('#weatherchips .chip').forEach(c => c.addEventListener('click', () => { $('voice_weather').value = c.dataset.w; queueSave();
    document.querySelectorAll('#weatherchips .chip').forEach(x=>x.classList.toggle('on', x===c)); }));
  setInterval(async () => { const r2 = await fetch('api.php?fn=state'); if (r2.ok) { const fresh = await r2.json();
    S.mac_last_sync = fresh.mac_last_sync; S.mac_last_run = fresh.mac_last_run; renderSync(); } }, 60000);
}
boot();
</script>
<?php endif; ?>
</body>
</html>
