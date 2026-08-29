<?php
// alexa-garden.php — zero-speech Alexa endpoint for the "daily garden" custom skill.
// Responds to LaunchRequest with ONLY an AudioPlayer.Play directive (no outputSpeech),
// so playback starts cold: no spoken intro at all. The stream URL comes from the
// daily brief's own alexa-feed.json, so skip/off mornings automatically play silence.
// Dev-only skill on Ben's account; never certified, so no signature verification.
header('Content-Type: application/json');

$raw  = file_get_contents('php://input');
$req  = json_decode($raw, true);
$type   = isset($req['request']['type']) ? $req['request']['type'] : '';
$intent = isset($req['request']['intent']['name']) ? $req['request']['intent']['name'] : '';

function garden_stream_url() {
    $ctx = stream_context_create(array('http' => array('timeout' => 4)));
    $feed = @file_get_contents('https://bdmartel.github.io/daily-brief/alexa-feed.json', false, $ctx);
    if ($feed) {
        $j = json_decode($feed, true);
        if ($j && !empty($j['streamUrl'])) return $j['streamUrl'];
    }
    return 'https://bdmartel.github.io/daily-brief/audio/wakeup-echo.mp3?v=' . date('Ymd');
}

function garden_play() {
    return array('version' => '1.0', 'response' => array(
        'shouldEndSession' => true,
        'directives' => array(array(
            'type' => 'AudioPlayer.Play',
            'playBehavior' => 'REPLACE_ALL',
            'audioItem' => array('stream' => array(
                'url' => garden_stream_url(),
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
