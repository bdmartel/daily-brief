<?php
// alexa-garden.php — zero-speech Alexa endpoint for the "daily garden" custom skill.
// Responds to LaunchRequest with ONLY an AudioPlayer.Play directive (no outputSpeech),
// so playback starts cold: no spoken intro at all. The stream URL comes from the
// daily brief's own alexa-feed.json, so skip/off mornings automatically play silence.
// Dev-only skill on Ben's account; never certified, so no signature verification.
header('Content-Type: application/json');
date_default_timezone_set('America/New_York');

$raw  = file_get_contents('php://input');
$req  = json_decode($raw, true);
$type   = isset($req['request']['type']) ? $req['request']['type'] : '';
$intent = isset($req['request']['intent']['name']) ? $req['request']['intent']['name'] : '';

function garden_stream_url() {
    $ctx = stream_context_create(array('http' => array('timeout' => 4)));
    $feed = @file_get_contents('https://bdmartel.github.io/daily-brief/alexa-feed.json', false, $ctx);
    if ($feed) {
        $j = json_decode($feed, true);
        if ($j && !empty($j['streamUrl'])) {
            // The feed can lag a few minutes behind the morning's push (Pages cache). If it still
            // names an older morning and today's file is already on Cloudflare, play today's.
            // A silence feed (alarm off / skip) is left alone.
            $u = $j['streamUrl'];
            if (strpos($u, 'silence') === false && strpos($u, '/m/' . date('Y-m-d') . '/') === false) {
                $today = morning_stream_url(date('Y-m-d'));
                if ($today) return $today;
            }
            return $u;
        }
    }
    // Feed unreachable: the newest morning's wake-up on Cloudflare (tools/sounds.py, 2026-10-16)
    return 'https://brief-sounds.bdmartel.workers.dev/latest/wakeup-echo.mp3';
}

// A past morning (Ben, 2026-11-16: "listen to yesterday's"). Mornings from Oct 16 on live at
// m/<date>/ on Cloudflare; returns null when that morning has no wake-up file.
function morning_stream_url($ymd) {
    $url = 'https://brief-sounds.bdmartel.workers.dev/m/' . $ymd . '/wakeup-echo.mp3';
    $ctx = stream_context_create(array('http' => array('method' => 'HEAD', 'timeout' => 4, 'ignore_errors' => true)));
    $h = @get_headers($url, false, $ctx);
    return ($h && strpos($h[0], '200') !== false) ? $url : null;
}

function say($text) {
    return array('version' => '1.0', 'response' => array(
        'shouldEndSession' => true,
        'outputSpeech' => array('type' => 'PlainText', 'text' => $text),
    ));
}

function garden_play($url = null) {
    return array('version' => '1.0', 'response' => array(
        'shouldEndSession' => true,
        'directives' => array(array(
            'type' => 'AudioPlayer.Play',
            'playBehavior' => 'REPLACE_ALL',
            'audioItem' => array('stream' => array(
                'url' => $url ? $url : garden_stream_url(),
                'token' => 'garden-' . date('Ymd-His'),
                'offsetInMilliseconds' => 0,
            )),
        )),
    ));
}

function garden_stop() {
    return array('version' => '1.0', 'response' => array(
        'shouldEndSession' => true,
        'directives' => array(array('type' => 'AudioPlayer.Stop')),
    ));
}

if ($type === 'LaunchRequest') {
    $out = garden_play();
} elseif ($type === 'IntentRequest') {
    if ($intent === 'PlayGardenIntent' || $intent === 'AMAZON.ResumeIntent') {
        $out = garden_play();
    } elseif ($intent === 'PlayYesterdayIntent' || $intent === 'PlayDayIntent') {
        $ymd = date('Y-m-d', strtotime('-1 day'));
        if ($intent === 'PlayDayIntent') {
            $v = isset($req['request']['intent']['slots']['day']['value']) ? $req['request']['intent']['slots']['day']['value'] : '';
            if (preg_match('/^\d{4}-\d{2}-\d{2}$/', $v)) {
                $ymd = $v;
                if ($ymd > date('Y-m-d')) $ymd = (intval(substr($ymd, 0, 4)) - 1) . substr($ymd, 4);  // "November 12" said in a later year
            }
        }
        $url = morning_stream_url($ymd);
        $out = $url ? garden_play($url) : say("I don't have a recording for " . date('F j', strtotime($ymd)) . '.');
    } elseif ($intent === 'AMAZON.PauseIntent' || $intent === 'AMAZON.StopIntent' || $intent === 'AMAZON.CancelIntent') {
        $out = garden_stop();
    } else {
        $out = array('version' => '1.0', 'response' => array('shouldEndSession' => true));
    }
} elseif (strpos($type, 'AudioPlayer.') === 0 || strpos($type, 'PlaybackController.') === 0 || $type === 'SessionEndedRequest') {
    // Playback lifecycle events: acknowledge with an empty response body.
    $out = array('version' => '1.0', 'response' => new stdClass());
} else {
    // Health check / GET
    $out = array('ok' => true, 'skill' => 'daily-garden', 'stream' => garden_stream_url());
}

echo json_encode($out);
