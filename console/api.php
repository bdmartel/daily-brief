<?php
// Morning Console API — state store + versions + previews for the daily-brief
// God-mode dashboard.
// Auth: PHP session (dashboard UI, password gate) OR Bearer token (the Mac's
// pull/ack; token lives in /var/www/tasks-private/morning-config.php + ~/.claude/.env).
// State:    /var/www/tasks-private/morning-state.json     (outside the docroot)
// Versions: /var/www/tasks-private/morning-versions.json  (named snapshots)
// Keys for previews (ANTHROPIC/OPENAI) also live in morning-config.php.
declare(strict_types=1);
date_default_timezone_set('America/New_York');
session_start();

$PRIV = '/var/www/tasks-private';
$STATE_FILE = $PRIV . '/morning-state.json';
$VERSIONS_FILE = $PRIV . '/morning-versions.json';
$CONFIG = $PRIV . '/morning-config.php';
$TOKEN = ''; $ANTHROPIC = ''; $OPENAI = '';
if (is_file($CONFIG)) {
  require $CONFIG;
  $TOKEN = defined('MORNING_TOKEN') ? MORNING_TOKEN : '';
  $ANTHROPIC = defined('MORNING_ANTHROPIC_KEY') ? MORNING_ANTHROPIC_KEY : '';
  $OPENAI = defined('MORNING_OPENAI_KEY') ? MORNING_OPENAI_KEY : '';
}

header('Content-Type: application/json');

function fail(string $m, int $c = 400): void { http_response_code($c); echo json_encode(['error' => $m]); exit; }

function bearer(): string {
  $h = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
  return preg_match('/^Bearer\s+(\S+)$/i', $h, $m) ? $m[1] : '';
}
$is_token = $TOKEN !== '' && hash_equals($TOKEN, bearer());
$is_session = !empty($_SESSION['morning_auth']);

// The next morning a change lands on: before 6 AM it's still "tonight's morning".
function next_morning(): string {
  return (int)date('G') < 6 ? date('Y-m-d') : date('Y-m-d', strtotime('+1 day'));
}

const DEFAULTS = [
  'alarm_enabled' => true,
  'skip_date' => '',
  'wake_hour' => null, 'wake_date' => '',
  'alarm_volume' => 70,
  'garden_enabled' => true,
  'garden_solo_seconds' => 180,
  'voice_weather' => '',
  'whisper' => '', 'whisper_date' => '',
  'doorway' => '', 'doorway_date' => '',
  'tasks_enabled' => true, 'comms_enabled' => true, 'mirror_enabled' => true,
  'refrain_text' => '', 'intro_override' => '', 'affirmations_text' => '',
  'hold' => false,
  'updated_at' => '', 'mac_last_sync' => '', 'mac_last_run' => '',
];

// What a named version captures: the reusable personality of a morning.
// One-shots (whisper, doorway, wake hour, skip) are moment-bound and excluded.
const VERSION_KEYS = ['alarm_enabled','alarm_volume','garden_enabled','garden_solo_seconds',
  'voice_weather','tasks_enabled','comms_enabled','mirror_enabled',
  'refrain_text','intro_override','affirmations_text'];

function load_json(string $file, $fallback) {
  $d = is_file($file) ? json_decode((string)file_get_contents($file), true) : null;
  return $d ?? $fallback;
}
function save_json(string $file, $data): void {
  $tmp = $file . '.tmp';
  file_put_contents($tmp, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES), LOCK_EX);
  rename($tmp, $file);
}
function load_state(string $file): array { return array_merge(DEFAULTS, load_json($file, [])); }

function clamp_state(array $s): array {
  $s['alarm_volume'] = max(30, min(100, (int)$s['alarm_volume']));
  $s['garden_solo_seconds'] = max(0, min(300, (int)$s['garden_solo_seconds']));
  if ($s['wake_hour'] !== null && $s['wake_hour'] !== '') $s['wake_hour'] = max(5, min(11, (int)$s['wake_hour']));
  return $s;
}

$fn = $_GET['fn'] ?? '';
$body = json_decode((string)file_get_contents('php://input'), true) ?: [];

if ($fn === 'login') {
  if (($body['pw'] ?? '') === 'm') { $_SESSION['morning_auth'] = true; echo json_encode(['ok' => true]); }
  else fail('wrong word', 403);
  exit;
}

if (!$is_token && !$is_session) fail('unauthorized', 401);

if ($fn === 'state') {
  $s = load_state($STATE_FILE);
  $s['next_morning'] = next_morning();
  echo json_encode($s);
  exit;
}

if ($fn === 'save') {
  $s = load_state($STATE_FILE);
  // HOLD: while held, nothing changes except releasing the hold itself.
  if (!empty($s['hold']) && empty($body['_unhold'])) fail('held', 423);
  if (!empty($body['_unhold'])) $s['hold'] = false;
  if (!empty($body['_hold']))   $s['hold'] = true;
  $editable = array_merge(VERSION_KEYS, ['skip_date','wake_hour','wake_date','whisper','whisper_date','doorway','doorway_date']);
  foreach ($editable as $k) if (array_key_exists($k, $body)) $s[$k] = $body[$k];
  if (!empty($body['_stamp_whisper'])) $s['whisper_date'] = $s['whisper'] !== '' ? next_morning() : '';
  if (!empty($body['_stamp_doorway'])) $s['doorway_date'] = $s['doorway'] !== '' ? next_morning() : '';
  if (!empty($body['_stamp_wake']))    $s['wake_date']    = $s['wake_hour'] ? next_morning() : '';
  if (!empty($body['_skip_next']))     $s['skip_date']    = next_morning();
  if (!empty($body['_unskip']))        $s['skip_date']    = '';
  $s = clamp_state($s);
  $s['updated_at'] = date('c');
  save_json($STATE_FILE, $s);
  $s['next_morning'] = next_morning();
  echo json_encode($s);
  exit;
}

// ---------- Versions ----------
if ($fn === 'versions') {
  echo json_encode(['versions' => load_json($VERSIONS_FILE, [])]);
  exit;
}

if ($fn === 'save_version') {
  $name = trim((string)($body['name'] ?? ''));
  if ($name === '') fail('name required');
  if (mb_strlen($name) > 60) $name = mb_substr($name, 0, 60);
  $s = load_state($STATE_FILE);
  $v = load_json($VERSIONS_FILE, []);
  $snap = [];
  foreach (VERSION_KEYS as $k) $snap[$k] = $s[$k];
  array_unshift($v, ['id' => bin2hex(random_bytes(6)), 'name' => $name, 'created' => date('c'), 'knobs' => $snap]);
  $v = array_slice($v, 0, 50);   // keep the shelf finite
  save_json($VERSIONS_FILE, $v);
  echo json_encode(['ok' => true, 'versions' => $v]);
  exit;
}

if ($fn === 'restore_version') {
  $s = load_state($STATE_FILE);
  if (!empty($s['hold'])) fail('held', 423);
  $id = $body['id'] ?? '';
  if ($id === 'original') {
    $knobs = [];
    foreach (VERSION_KEYS as $k) $knobs[$k] = DEFAULTS[$k];
  } else {
    $knobs = null;
    foreach (load_json($VERSIONS_FILE, []) as $ver) if ($ver['id'] === $id) { $knobs = $ver['knobs']; break; }
    if ($knobs === null) fail('version not found', 404);
  }
  foreach (VERSION_KEYS as $k) if (array_key_exists($k, $knobs)) $s[$k] = $knobs[$k];
  $s = clamp_state($s);
  $s['updated_at'] = date('c');
  save_json($STATE_FILE, $s);
  $s['next_morning'] = next_morning();
  echo json_encode($s);
  exit;
}

if ($fn === 'delete_version') {
  $id = $body['id'] ?? '';
  $v = array_values(array_filter(load_json($VERSIONS_FILE, []), fn($x) => $x['id'] !== $id));
  save_json($VERSIONS_FILE, $v);
  echo json_encode(['ok' => true, 'versions' => $v]);
  exit;
}

if ($fn === 'ack') {
  $s = load_state($STATE_FILE);
  $s['mac_last_sync'] = date('c');
  if (!empty($body['ran'])) $s['mac_last_run'] = date('c');
  save_json($STATE_FILE, $s);
  echo json_encode(['ok' => true]);
  exit;
}

// ---------- Previews (generated with the same recipe the morning uses) ----------

function season_label(): string {
  $m = (int)date('n', strtotime(next_morning()));
  $map = [12=>'deep winter',1=>'midwinter',2=>'late winter',3=>'early spring',4=>'full spring',
          5=>'late spring',6=>'early summer',7=>'high summer',8=>'late summer',9=>'early fall',
          10=>'deep fall',11=>'late fall'];
  return $map[$m];
}

const POEM_ENTRIES = [
  'sound'    => 'a specific sound, near or far',
  'hands'    => 'something his hands know well — a texture, a tool, a latch, a handle',
  'animal'   => 'an animal or bird caught mid-act, doing exactly what it does',
  'weather'  => 'weather in motion — fog lifting, heat building, wind working the trees, rain coming or going',
  'object'   => 'an object sitting exactly where it was left',
  'body'     => 'the body waking — breath, weight, warmth, feet finding the floor',
  'halfmade' => 'something outdoors caught mid-change — half-open, half-grown, half-finished',
  'smell'    => 'a smell that belongs to this time of year',
];

// The refrain + pool as they live on the Mac today (fallbacks for preview when
// the console's editors are blank, i.e. "leave the Mac's files alone").
const CANON_REFRAIN = "You don't have to be ready. You only have to be here.\nWhat you started is still becoming.\nSo — up.";
const CANON_POOL = [
  'I become the thoughts I repeat — so I choose them on purpose.',
  'My emotions are messengers, not commands; I listen, then I lead.',
  'Anxiety is just my mind living too far ahead — I can come home to now.',
  'Motivation is unreliable; my habits are what carry me.',
  'My past is a chapter, not a home — I don\'t live there anymore.',
  'I release what I can\'t control and put my hands on what I can.',
  'I move like water — I adapt, I keep flowing, I find the way around.',
  'I am the address — I don\'t need to land anywhere else to be home.',
];

function anthropic_gen(string $key, string $prompt, int $max = 1024): string {
  $ch = curl_init('https://api.anthropic.com/v1/messages');
  curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT => 90,
    CURLOPT_HTTPHEADER => ['content-type: application/json', 'x-api-key: ' . $key, 'anthropic-version: 2023-06-01'],
    CURLOPT_POSTFIELDS => json_encode([
      'model' => 'claude-opus-4-8', 'max_tokens' => $max,
      'messages' => [['role' => 'user', 'content' => $prompt]],
    ]),
  ]);
  $res = curl_exec($ch);
  if ($res === false) fail('generation failed: ' . curl_error($ch), 502);
  $d = json_decode((string)$res, true);
  if (!isset($d['content'][0]['text'])) fail('generation failed: ' . substr((string)$res, 0, 200), 502);
  $out = '';
  foreach ($d['content'] as $b) if (($b['type'] ?? '') === 'text') $out .= $b['text'];
  return trim($out);
}

if ($fn === 'preview') {
  if ($ANTHROPIC === '') fail('preview key not configured', 501);
  $s = load_state($STATE_FILE);
  $section = $body['section'] ?? '';
  $nm = next_morning();
  $season = season_label();
  $date_label = date('l, F j, Y', strtotime($nm));

  if ($section === 'intro') {
    if ($s['intro_override'] !== '' && $s['intro_override'] !== 'auto') {
      echo json_encode(['text' => $s['intro_override'], 'note' => 'fixed override — read verbatim every morning until cleared']);
      exit;
    }
    $whisper = ($s['whisper'] !== '' && $s['whisper_date'] === $nm)
      ? " Ben left himself a note last night for this morning — weave its substance in naturally as part of the wake-up (never read it out like a list, never call it a note): {$s['whisper']}."
      : '';
    $p = "Write a very short spoken wake-up for Ben — 3 to 4 sentences, read aloud at 6 AM right before his morning poem. Ease him awake: warm and unhurried, with one light, clever wink (gentle humor, never forced or corny) that makes him smile, yet it should still land like a small beautiful sentiment. Then turn him gently toward the poem that's coming, so he's ready to take it in. Ben is building a farming life in the New Hampshire hills; it is {$season}.{$whisper} Second person, spoken aloud, no markdown, no lists, no headers. Output only the wake-up.";
    echo json_encode(['text' => anthropic_gen($ANTHROPIC, $p, 512)]);
    exit;
  }

  if ($section === 'poem') {
    $doorway = ($s['doorway'] !== '' && $s['doorway_date'] === $nm && isset(POEM_ENTRIES[$s['doorway']]))
      ? POEM_ENTRIES[$s['doorway']]
      : array_values(POEM_ENTRIES)[ (int)date('z', strtotime($nm)) % 8 ];
    $refrain = $s['refrain_text'] !== '' ? $s['refrain_text'] : CANON_REFRAIN;
    $p = "Write a fuller morning verse, 8 to 12 lines (about twice the length of a short poem), for Ben, who is building a farming life in the New Hampshire hills. It is {$date_label}, {$season}. Enter the poem through {$doorway}, and let it develop from there — take your time, build an image or two honestly rather than rushing. Warm, a little husky, image-rich, plainspoken, never saccharine.\n\nHard rules — these moves are worn out and banned:\n- Do not open on morning light arriving or dawn spreading. Light may appear later in the poem, but it must not begin there.\n- No before-and-after of his life. Never contrast a past city or fashion life with the farm. The poem lives entirely in the present.\n- Do not end on crops or green things growing on their own, without him, or while he sleeps.\n\nThese fixed lines will follow immediately, so lead naturally toward them but do NOT repeat them:\n\n{$refrain}\n\nOutput ONLY the new verse lines, nothing else.";
    $verse = anthropic_gen($ANTHROPIC, $p, 768);
    echo json_encode(['text' => $verse . "\n\n" . $refrain,
      'note' => 'live mornings also re-word the refrain\'s upper lines daily and avoid yesterday\'s images']);
    exit;
  }

  if ($section === 'mirror') {
    $pool = [];
    if ($s['affirmations_text'] !== '') {
      foreach (preg_split('/\R/', $s['affirmations_text']) as $line) {
        $line = trim($line);
        if ($line !== '' && $line[0] !== '#') $pool[] = $line;
      }
    }
    if (!$pool) $pool = CANON_POOL;
    shuffle($pool);
    $picks = implode("\n", array_slice($pool, 0, random_int(1, 2)));
    $p = "Ben does mirror work each morning — standing at the mirror, saying something true to himself out loud. Take the affirmation(s) below and turn it into today's short spoken \"mirror moment.\" Don't just state it — go INTO it: gently set it up, unpack what it really means and why it matters for him right now, the way a steady, warm friend would coach him through it at the mirror. Build to the affirmation, deliver it plainly, then tell him to say it to himself. Unhurried and intimate, 4 to 7 sentences. Vary the angle so it feels fresh and a little surprising, never formulaic. Spoken aloud, second person, ending on the first-person line he repeats. No markdown, no lists, no headers. Output only the mirror moment.\n\n{$picks}";
    echo json_encode(['text' => anthropic_gen($ANTHROPIC, $p, 512), 'note' => 'drawn at random from the pool — every morning picks differently']);
    exit;
  }

  fail('unknown section', 404);
}

if ($fn === 'preview_tts') {
  if ($OPENAI === '') fail('tts key not configured', 501);
  $text = trim((string)($body['text'] ?? ''));
  if ($text === '') fail('text required');
  if (mb_strlen($text) > 4000) $text = mb_substr($text, 0, 4000);
  $s = load_state($STATE_FILE);
  $instr = 'Warm, slightly husky female voice. Tomboyish but attractive. Speak from the chest, not the nose. '
         . 'You are actually thinking about what you are reading -- you understand the scene and you care about the words. '
         . 'Natural conversational pace, not slow or dramatic. Pause meaningfully before lines that land, like a good writer '
         . 'reading their own work. Smart, engaged, present. Not performative.';
  if ($s['voice_weather'] !== '') $instr .= " Today's added direction, layered on all of that: {$s['voice_weather']}.";
  $ch = curl_init('https://api.openai.com/v1/audio/speech');
  curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT => 90,
    CURLOPT_HTTPHEADER => ['Content-Type: application/json', 'Authorization: Bearer ' . $OPENAI],
    CURLOPT_POSTFIELDS => json_encode([
      'model' => 'gpt-4o-mini-tts', 'voice' => 'shimmer', 'input' => $text,
      'instructions' => $instr, 'response_format' => 'mp3',
    ]),
  ]);
  $res = curl_exec($ch);
  $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
  if ($res === false || $code !== 200) fail('tts failed: ' . substr((string)$res, 0, 200), 502);
  echo json_encode(['audio' => base64_encode((string)$res)]);
  exit;
}

fail('unknown fn', 404);
