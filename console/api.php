<?php
// Morning Console API — state store for the daily-brief God-mode dashboard.
// Auth: PHP session (dashboard UI, password gate) OR Bearer token (the Mac's
// pull/ack, token lives in /var/www/tasks-private/morning-config.php + ~/.claude/.env).
// State: /var/www/tasks-private/morning-state.json (outside the docroot).
declare(strict_types=1);
date_default_timezone_set('America/New_York');
session_start();

$PRIV = '/var/www/tasks-private';
$STATE_FILE = $PRIV . '/morning-state.json';
$CONFIG = $PRIV . '/morning-config.php';
$TOKEN = '';
if (is_file($CONFIG)) { require $CONFIG; $TOKEN = defined('MORNING_TOKEN') ? MORNING_TOKEN : ''; }

header('Content-Type: application/json');

function fail(string $m, int $c = 400): void { http_response_code($c); echo json_encode(['error' => $m]); exit; }

function bearer(): string {
  $h = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
  return preg_match('/^Bearer\s+(\S+)$/i', $h, $m) ? $m[1] : '';
}
$is_token = $TOKEN !== '' && hash_equals($TOKEN, bearer());
$is_session = !empty($_SESSION['morning_auth']);

// The next morning this change should land on: before 6 AM it's still "tonight's
// morning"; after 6 AM the next morning is tomorrow.
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
  'updated_at' => '', 'mac_last_sync' => '', 'mac_last_run' => '',
];

function load_state(string $file): array {
  $d = is_file($file) ? json_decode((string)file_get_contents($file), true) : null;
  return array_merge(DEFAULTS, is_array($d) ? $d : []);
}
function save_state(string $file, array $s): void {
  $tmp = $file . '.tmp';
  file_put_contents($tmp, json_encode($s, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES), LOCK_EX);
  rename($tmp, $file);
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
  $editable = ['alarm_enabled','skip_date','wake_hour','wake_date','alarm_volume','garden_enabled',
               'garden_solo_seconds','voice_weather','whisper','whisper_date','doorway','doorway_date',
               'tasks_enabled','comms_enabled','mirror_enabled','refrain_text','intro_override','affirmations_text'];
  foreach ($editable as $k) if (array_key_exists($k, $body)) $s[$k] = $body[$k];
  // One-shots sent as bare intents get stamped with the morning they target.
  if (!empty($body['_stamp_whisper'])) $s['whisper_date'] = $s['whisper'] !== '' ? next_morning() : '';
  if (!empty($body['_stamp_doorway'])) $s['doorway_date'] = $s['doorway'] !== '' ? next_morning() : '';
  if (!empty($body['_stamp_wake']))    $s['wake_date']    = $s['wake_hour'] ? next_morning() : '';
  if (!empty($body['_skip_next']))     $s['skip_date']    = next_morning();
  if (!empty($body['_unskip']))        $s['skip_date']    = '';
  // Sanity clamps
  $s['alarm_volume'] = max(30, min(100, (int)$s['alarm_volume']));
  $s['garden_solo_seconds'] = max(0, min(300, (int)$s['garden_solo_seconds']));
  if ($s['wake_hour'] !== null && $s['wake_hour'] !== '') $s['wake_hour'] = max(5, min(11, (int)$s['wake_hour']));
  $s['updated_at'] = date('c');
  save_state($STATE_FILE, $s);
  $s['next_morning'] = next_morning();
  echo json_encode($s);
  exit;
}

if ($fn === 'ack') {   // the Mac reports it pulled (and optionally that a brief ran)
  $s = load_state($STATE_FILE);
  $s['mac_last_sync'] = date('c');
  if (!empty($body['ran'])) $s['mac_last_run'] = date('c');
  save_state($STATE_FILE, $s);
  echo json_encode(['ok' => true]);
  exit;
}

fail('unknown fn', 404);
