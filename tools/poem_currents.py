#!/usr/bin/env python3
"""The morning poem's doors, currents and memory (Ben, 2026-11-20).

Ben: "after listening for months I recognize them all and feel like I'm in Groundhog Day".
So the poem no longer cycles 8 fixed doors with one day of memory:
  - DOORS: a long catalog. Ben ticks the ones he wants at lists.benmartel.com/poem;
    each morning picks one he has not heard in the longest while (random among the
    least recent), so every ticked door comes round before any repeats.
  - CURRENTS: what is actually going on in the world this week (weather, moon, what is
    migrating, what is in bloom ...). Two per morning from the ticked ones, least
    recently used first. Weather, moon and daylight are live data (Open-Meteo, computed
    moon); the rest the model draws from what is true in the Monadnock region this week.
  - MEMORY: the last 20 poems (verse + motivator) are shown to the model as don't-reuse.

The catalog lives here and nowhere else: `page` writes the lists page from it.

  poem_currents.py pick   --date YYYY-MM-DD [--doorway KEY] --out DIR
        writes DIR/entry.txt, DIR/currents.txt, DIR/history.txt, DIR/motivators.txt, DIR/pick.json
  poem_currents.py record --date YYYY-MM-DD --verse FILE --motivator FILE --pick DIR/pick.json
  poem_currents.py page   --out ~/projects/lists/private/poem.html
  poem_currents.py seed   (fills the history from the archived pages, once)
  poem_currents.py picks  (prints what Ben has ticked)
"""
import argparse, datetime, json, math, os, random, subprocess, sys, urllib.request

HOME = os.path.expanduser('~')
REPO = os.path.join(HOME, 'projects', 'daily-brief')
HISTORY = os.path.join(HOME, '.claude', 'daily-brief-poem-history.jsonl')
PICKS_CACHE = os.path.join(HOME, '.claude', 'daily-brief-poem-picks.json')
DROPLET = 'root@178.128.155.186'
PICKS_REMOTE = '/var/www/lists/data/state/poem.json'
MEMORY = 20
LAT, LON, PLACE = 42.8706, -71.952, 'Peterborough, in the Monadnock region of southern New Hampshire'

# (key, short label for the list, what the model is told). The first 8 are the original rotation.
DOORS = [
    ('sound', 'A sound', 'a specific sound, near or far'),
    ('hands', 'Something the hands know', 'something his hands know well: a texture, a tool, a latch, a handle'),
    ('animal', 'An animal mid-act', 'an animal or bird caught mid-act, doing exactly what it does'),
    ('weather', 'Weather moving', 'weather in motion: fog lifting, heat building, wind working the trees, rain coming or going'),
    ('object', 'An object left where it was', 'an object sitting exactly where it was left'),
    ('body', 'The body waking', 'the body waking: breath, weight, warmth, feet finding the floor'),
    ('halfmade', 'Something half-finished outdoors', 'something outdoors caught mid-change: half-open, half-grown, half-finished'),
    ('smell', 'A smell of the season', 'a smell that belongs to this time of year'),
    ('taste', 'A taste', 'a taste: the first sip of something, an apple, cold water from the tap'),
    ('temperature', 'How cold or warm a thing is', 'the exact temperature of one thing touched: a doorknob, a mug, the floorboards, the truck door'),
    ('tool', 'One tool and its last job', 'a single tool and the job it was last used for'),
    ('window', 'One window', 'exactly what is framed in one window right now'),
    ('tracks', 'Tracks left overnight', 'tracks or traces left overnight in mud, frost, dust or snow, and who made them'),
    ('shadow', 'A shadow', 'a shadow and what is casting it'),
    ('water', 'Water doing something', 'water doing one thing: dripping, freezing, pooling, running in a ditch'),
    ('fire', 'Fire starting', 'fire starting: the woodstove, a match, kindling catching'),
    ('seed', 'A seed or bulb', 'a seed, bulb, clove or pit held in the hand, and what is folded inside it'),
    ('soil', 'A handful of soil', 'a handful of soil: its weight, its cold, its smell'),
    ('tree', 'One particular tree', 'one particular tree and what it is doing this week'),
    ('sky', 'The sky before sun', 'the sky before the sun is up: one color, one cloud'),
    ('leftover', 'What the night left', 'something the night left behind: dew, a fallen branch, a moth on the screen'),
    ('kitchen', 'A kitchen ritual', 'a kitchen ritual in progress: the kettle, the knife, the bread, the pan'),
    ('neighbor', 'A neighbor across the way', "a neighbor's light, sound or chimney smoke across the field"),
    ('road', 'The road outside', 'the road outside: a truck passing, gravel, the plow, a school bus'),
    ('insect', 'An insect', 'an insect: a fly on the glass, a spider line, a cricket in the wall'),
    ('color', 'One color', 'one color, and every place it shows up this morning'),
    ('silence', 'The kind of quiet', 'the quality of the quiet, and what is missing from it'),
    ('distance', 'Something far off', 'something far away: a ridge line, a train, a plane light, a dog barking miles off'),
    ('clothing', 'Boots, gloves, a coat', 'clothing waiting to be worn: boots by the door, gloves stiff on the stove, a coat on the hook'),
    ('birdcall', 'A bird call', "one bird's call, which bird it is, and what it is saying"),
    ('number', 'A number', 'a number: degrees on the thermometer, eggs in the box, steps to the barn, days until something'),
    ('truck', 'The truck', 'the truck in the cold: frost on the windshield, the engine turning over, the cab warming'),
    ('path', 'A worn path', 'a path worn by feet, deer or a wheelbarrow, and where it goes'),
    ('hum', 'A machine humming', "a machine's sound in the dark house: the pump, the fridge, the furnace kicking on"),
    ('yesterday', "Yesterday's work, still visible", "something his hands did yesterday, still visible this morning"),
    ('childhood', 'One childhood detail', 'one specific detail from childhood that this morning calls up'),
    ('question', 'A plain question', 'a plain question asked out loud, that the poem then lives inside'),
    ('list', 'A list of small true things', 'a short list of small things already true this morning'),
    ('instruction', 'A plain instruction', 'a plain instruction to himself, like "put on the boots", and what follows from it'),
    ('letter', 'A letter to someone', 'a short letter addressed to someone or something (a hill, a hen, the frost, his younger self)'),
    ('knot', 'A knot or fastening', 'a knot, a rope, a buckle, a gate chain: something fastened'),
    ('animal-voice', 'Spoken by an animal or thing', 'the voice of an animal or a thing in the room speaking to him (the fox, the woodstove, the field)'),
]
DOOR_DEFAULT = [k for k, _, _ in DOORS[:8]]
CONSOLE_DOORWAY = {'sound': 'sound', 'hands': 'hands', 'animal': 'animal', 'weather': 'weather',
                   'object': 'object', 'body': 'body', 'halfmade': 'halfmade', 'smell': 'smell'}

# (key, label, how the model is told to use it). live = built from data fetched this morning.
CURRENTS = [
    ('weather', "Today's weather", 'live'),
    ('moon', 'The moon', 'live'),
    ('migrating', "What's migrating", 'what birds, insects or animals are migrating through or out of the region this week'),
    ('bloom', "What's in bloom", "what is actually in bloom or flowering in the region this week (wild or garden), even if it is small or odd for the season"),
    ('daylight', 'Daylight gained or lost', 'live'),
    ('frost', 'Frost and the freeze line', 'live'),
    ('harvest', "What's being harvested or put up", 'what is being harvested, stored or put up on New England farms this week'),
    ('farmwork', "This week's farm work", 'the farm and garden work that belongs to this exact week of the year in New Hampshire'),
    ('wildlife', 'What animals are up to', 'what the local animals are doing this week (rut, denning, caching, molting, nesting, calling)'),
    ('insects', 'Insects this week', 'which insects are about, or gone, or overwintering, and how'),
    ('trees', 'What the trees are doing', 'what the trees are doing this week: leaf, bud, bark, sap, seed'),
    ('birds', "Who's singing or calling", 'which birds are present, singing or calling in the region this week'),
    ('soil', 'The state of the soil', 'the state of the ground this week: warm, cooling, frozen, thawing, wet, dry'),
    ('streams', 'Streams and ponds', 'what the streams, ponds and wetlands are doing this week: running high or low, skimming with ice, thawing'),
    ('stars', 'The night sky', 'what is in the night or pre-dawn sky this week: bright planets, a constellation rising, a meteor shower'),
    ('turn', 'Where the year stands', 'live'),
    ('oldcalendar', 'The old farm calendar', "the old farm calendar: the moon's folk name, a quarter or cross-quarter day, a planting or weather saying tied to this time of year"),
    ('forage', 'What can be gathered wild', 'what can be foraged or gathered wild this week (nuts, mushrooms, greens, rose hips, sap)'),
    ('table', "What's good to eat now", 'what is in season to eat in New England this week'),
    ('woodpile', 'Wood, stove and fuel', 'the season of wood: splitting, stacking, the first fires, the pile going down'),
    ('word', 'An old farm word', 'one old farming or country word that fits this week, used in the poem without explaining it'),
    ('history', 'On this day, long ago', 'something true that happened in New England farming or weather on or near this date long ago (only if you are sure it is true)'),
    ('notes', 'Your own day (from your notes)', 'notes'),
]
CURRENT_DEFAULT = ['weather', 'moon', 'migrating', 'bloom', 'notes']
PER_MORNING = 2   # currents per poem, besides 'notes'

WMO = {0: 'clear', 1: 'mostly clear', 2: 'partly cloudy', 3: 'overcast', 45: 'fog', 48: 'freezing fog',
       51: 'light drizzle', 53: 'drizzle', 55: 'heavy drizzle', 56: 'freezing drizzle', 57: 'freezing drizzle',
       61: 'light rain', 63: 'rain', 65: 'heavy rain', 66: 'freezing rain', 67: 'freezing rain',
       71: 'light snow', 73: 'snow', 75: 'heavy snow', 77: 'snow grains', 80: 'rain showers', 81: 'rain showers',
       82: 'heavy rain showers', 85: 'snow showers', 86: 'heavy snow showers', 95: 'thunderstorms',
       96: 'thunderstorms with hail', 99: 'thunderstorms with hail'}
FULL_MOON_NAMES = {1: 'Wolf Moon', 2: 'Snow Moon', 3: 'Worm Moon', 4: 'Pink Moon', 5: 'Flower Moon',
                   6: 'Strawberry Moon', 7: 'Buck Moon', 8: 'Sturgeon Moon', 9: 'Harvest or Corn Moon',
                   10: "Hunter's Moon", 11: 'Beaver Moon', 12: 'Cold Moon'}
COMPASS = ['north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest']


# ---------- Ben's ticks ----------
def load_picks():
    """Ben's ticks from the lists page (ssh), cached locally; defaults if never saved."""
    data = None
    try:
        out = subprocess.run(['ssh', '-o', 'ConnectTimeout=8', '-o', 'BatchMode=yes', DROPLET, f'cat {PICKS_REMOTE}'],
                             capture_output=True, text=True, timeout=20)
        if out.returncode == 0 and out.stdout.strip():
            data = json.loads(out.stdout)
            with open(PICKS_CACHE, 'w') as f:
                json.dump(data, f)
    except Exception:
        data = None
    if data is None:
        try:
            with open(PICKS_CACHE) as f:
                data = json.load(f)
        except Exception:
            data = {}
    dk = {k for k, _, _ in DOORS}
    ck = {k for k, _, _ in CURRENTS}
    doors = [k for k in data.get('doors', []) if k in dk] or list(DOOR_DEFAULT)
    currents = [k for k in data.get('currents', []) if k in ck] if 'currents' in data else list(CURRENT_DEFAULT)
    return doors, currents


# ---------- memory ----------
def read_history():
    rows = []
    try:
        with open(HISTORY, encoding='utf-8') as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    rows.sort(key=lambda r: r.get('date', ''))
    return rows


def write_history(rows):
    tmp = HISTORY + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    os.replace(tmp, HISTORY)


def choose_door(doors, rows, date, forced=None):
    if forced and forced in {k for k, _, _ in DOORS}:
        return forced
    last = {}
    for i, r in enumerate(rows):
        if r.get('door'):
            last[r['door']] = i
    # never-used doors first, then the ones heard longest ago; random among the oldest third
    rng = random.Random(date + 'door')
    ranked = sorted(doors, key=lambda k: (last.get(k, -1), rng.random()))   # ties broken at random
    pool = ranked[:max(1, math.ceil(len(ranked) / 3))]
    return rng.choice(pool)


def choose_currents(currents, rows, date):
    picks = [c for c in currents if c != 'notes']
    last = {}
    for i, r in enumerate(rows):
        for c in r.get('currents', []):
            last[c] = i
    rng = random.Random(date + 'cur')
    ranked = sorted(picks, key=lambda k: (last.get(k, -1), rng.random()))
    return ranked[:PER_MORNING]


# ---------- live data ----------
def fetch_weather(date):
    url = ('https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s'
           '&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset,daylight_duration,precipitation_sum,'
           'snowfall_sum,weather_code,wind_speed_10m_max,wind_direction_10m_dominant'
           '&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch'
           '&timezone=America%%2FNew_York&past_days=7&forecast_days=2') % (LAT, LON)
    with urllib.request.urlopen(url, timeout=15) as r:
        d = json.load(r)['daily']
    i = d['time'].index(date)
    return d, i


def moon(date):
    d = datetime.datetime.strptime(date, '%Y-%m-%d').replace(hour=6) - datetime.datetime(2000, 1, 6, 18, 14)
    syn = 29.530588853
    age = (d.total_seconds() / 86400) % syn
    illum = round((1 - math.cos(2 * math.pi * age / syn)) / 2 * 100)
    names = [(1.0, 'new'), (6.4, 'a waxing crescent'), (8.4, 'first quarter'), (13.8, 'waxing gibbous'),
             (15.8, 'full'), (21.1, 'waning gibbous'), (23.1, 'last quarter'), (28.5, 'a waning crescent'), (29.6, 'new')]
    phase = next(n for lim, n in names if age < lim)
    to_full = (14.765 - age) % syn
    full_day = datetime.datetime.strptime(date, '%Y-%m-%d') + datetime.timedelta(days=to_full)
    rise = {'new': 'rises and sets with the sun, unseen',
            'a waxing crescent': 'sets in the evening a little after the sun',
            'first quarter': 'is high at sunset and sets around midnight',
            'waxing gibbous': 'rises in the afternoon and is up most of the night',
            'full': 'rises at sunset and sets at dawn, low in the west as he wakes',
            'waning gibbous': 'is still up in the west at dawn',
            'last quarter': 'is high in the south at dawn',
            'a waning crescent': 'rises in the east before dawn, a thin sliver'}[phase]
    return (f'The moon is {phase}, {illum}% lit; it {rise}. The next full moon is the '
            f'{FULL_MOON_NAMES[full_day.month]}, in {round(to_full)} days.')


def year_turn(date):
    d = datetime.date.fromisoformat(date)
    marks = [(datetime.date(d.year, 3, 20), 'the spring equinox'), (datetime.date(d.year, 6, 21), 'the summer solstice'),
             (datetime.date(d.year, 9, 22), 'the fall equinox'), (datetime.date(d.year, 12, 21), 'the winter solstice'),
             (datetime.date(d.year + 1, 3, 20), 'the spring equinox')]
    nxt = next((m for m in marks if m[0] >= d))
    prev = [m for m in marks if m[0] < d]
    s = f'{(nxt[0] - d).days} days until {nxt[1]}'
    if prev:
        s += f'; {(d - prev[-1][0]).days} days since {prev[-1][1]}'
    return s + '.'


def live_text(key, date, wx):
    if key == 'moon':
        return moon(date)
    if key == 'turn':
        return 'Where the year stands: ' + year_turn(date)
    if not wx:
        return None
    d, i = wx
    if key == 'weather':
        wind = COMPASS[round(d['wind_direction_10m_dominant'][i] / 45) % 8]
        s = (f"Today in {PLACE.split(',')[0]}: {WMO.get(d['weather_code'][i], 'mixed')}, high {round(d['temperature_2m_max'][i])}°F, "
             f"overnight low {round(d['temperature_2m_min'][i])}°F, wind from the {wind} up to {round(d['wind_speed_10m_max'][i])} mph")
        rain = d['precipitation_sum'][i]
        snow = d.get('snowfall_sum', [0] * len(d['time']))[i]
        s += f', {rain:.2f} in of rain or melt' if rain >= 0.02 else ', no rain'
        if snow and snow >= 0.1:
            s += f', {snow:.1f} in of snow'
        week = sum(x or 0 for x in d['precipitation_sum'][max(0, i - 7):i])
        s += f'. The past week brought {week:.2f} in of rain in all.'
        return s
    if key == 'daylight':
        today = d['daylight_duration'][i]
        wk = d['daylight_duration'][max(0, i - 7)]
        diff = round((today - wk) / 60)
        h, m = divmod(round(today / 60), 60)
        sr, ss = d['sunrise'][i][11:], d['sunset'][i][11:]
        return (f'Sunrise {sr}, sunset {ss}: {h} h {m} min of daylight, '
                f"{abs(diff)} minutes {'less' if diff < 0 else 'more'} than a week ago.")
    if key == 'frost':
        lows = [round(x) for x in d['temperature_2m_min'][max(0, i - 7):i + 1]]
        frosts = sum(1 for x in lows if x <= 32)
        hard = sum(1 for x in lows if x <= 28)
        return (f'Overnight lows this past week: {", ".join(map(str, lows))}°F; '
                f'{frosts} frosts, {hard} hard freezes (28°F or below). Last night: {lows[-1]}°F.')
    return None


def currents_block(chosen, use_notes, date):
    try:
        wx = fetch_weather(date)
    except Exception:
        wx = None
    label = {k: (lab, how) for k, lab, how in CURRENTS}
    lines = []
    for k in chosen:
        lab, how = label[k]
        if how == 'live':
            t = live_text(k, date, wx)
            if t:
                lines.append(f'- {lab}: {t}')
        else:
            extra = ''
            if k in ('soil', 'streams', 'forage', 'farmwork', 'woodpile') and wx:
                extra = ' Real conditions to stay true to: ' + (live_text('weather', date, wx) or '') + ' ' + (live_text('frost', date, wx) or '')
            lines.append(f'- {lab}: {how}. Use what is really true for {PLACE} this week; do not invent anything unlikely.{extra}')
    return lines, use_notes


# ---------- commands ----------
def cmd_pick(a):
    doors, currents = load_picks()
    rows = read_history()
    forced = CONSOLE_DOORWAY.get(a.doorway or '')
    door = choose_door(doors, rows, a.date, forced)
    chosen = choose_currents(currents, rows, a.date)
    lines, use_notes = currents_block(chosen, 'notes' in currents, a.date)
    os.makedirs(a.out, exist_ok=True)
    text = {k: t for k, _, t in DOORS}
    with open(os.path.join(a.out, 'entry.txt'), 'w') as f:
        f.write(text[door])
    cur = ''
    if lines:
        cur = ('What is really going on in the world this morning (live facts and this week in the region). '
               'Let one or both of these shape the poem\'s subject and images, woven in as things he could see, hear or feel, '
               'not as a report. Keep any numbers only if they sound natural spoken aloud:\n' + '\n'.join(lines))
    with open(os.path.join(a.out, 'currents.txt'), 'w') as f:
        f.write(cur)
    past = [r for r in rows if r.get('date', '') < a.date][-MEMORY:]
    hist = ''
    if past:
        hist = (f'- The last {len(past)} morning poems are below, oldest first, between the dashes. Do not reuse their opening moves, '
                'their central images, their objects, their animals or their ways of ending. Find something none of them touched.\n---\n'
                + '\n---\n'.join(r['verse'].strip() for r in past if r.get('verse')) + '\n---\n')
    with open(os.path.join(a.out, 'history.txt'), 'w') as f:
        f.write(hist)
    mots = [r['motivator'].strip() for r in past if r.get('motivator')]
    with open(os.path.join(a.out, 'motivators.txt'), 'w') as f:
        f.write('\n'.join(f'- {m}'.replace('\n', ' / ') for m in mots))
    with open(os.path.join(a.out, 'pick.json'), 'w') as f:
        json.dump({'door': door, 'currents': chosen, 'notes': use_notes, 'facts': lines}, f, ensure_ascii=False)
    print(json.dumps({'door': door, 'currents': chosen, 'notes': use_notes}))


def cmd_record(a):
    with open(a.verse, encoding='utf-8') as f:
        verse = f.read().strip()
    mot = ''
    if a.motivator and os.path.exists(a.motivator):
        with open(a.motivator, encoding='utf-8') as f:
            mot = f.read().strip()
    pick = {}
    if a.pick and os.path.exists(a.pick):
        with open(a.pick) as f:
            pick = json.load(f)
    rows = [r for r in read_history() if r.get('date') != a.date]
    rows.append({'date': a.date, 'door': pick.get('door', ''), 'currents': pick.get('currents', []),
                 'verse': verse, 'motivator': mot})
    rows.sort(key=lambda r: r['date'])
    write_history(rows[-120:])


def cmd_seed(a):
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    import html as H, re
    from all_poems import gather
    found = gather(REPO)
    have = {r['date'] for r in read_history()}
    rows = read_history()
    for day in sorted(found)[-MEMORY:]:
        ds = day.isoformat()
        if ds in have:
            continue
        txt = H.unescape(re.sub(r'<br\s*/?>', '\n', found[day]['text']))
        txt = re.sub(r'<[^>]+>', '', txt).strip()
        txt = '\n'.join(l for l in txt.split('\n') if not re.match(r'(?i)^[\s"“”]*so\s*[—–\-,]*\s*up\s*[.!?…"“”]*\s*$', l)).strip()
        parts = re.split(r'\n\s*\n', txt)
        verse, mot = (('\n\n'.join(parts[:-1]), parts[-1]) if len(parts) > 1 else (txt, ''))
        rows.append({'date': ds, 'door': '', 'currents': [], 'verse': verse.strip(), 'motivator': mot.strip(), 'seeded': True})
    rows.sort(key=lambda r: r['date'])
    write_history(rows)
    print(f'history: {len(rows)} poems')


def cmd_made(a):
    """HTML note for the brief: how this morning's poem was made (Ben, Nov 20, 2026: shown Nov 21 to 27)."""
    import html
    pk = json.load(open(a.pick))
    dlab = {k: (lab, t) for k, lab, t in DOORS}
    clab = {k: (lab, how) for k, lab, how in CURRENTS}
    e = html.escape
    lab, t = dlab.get(pk.get('door'), (pk.get('door', ''), ''))
    rows = [f'<li><b>The way in:</b> {e(lab)} ({e(t)}).</li>']
    for k in pk.get('currents', []):
        cl, how = clab.get(k, (k, ''))
        fact = next((f[len(f'- {cl}: '):] for f in pk.get('facts', []) if f.startswith(f'- {cl}: ')), '')
        if how == 'live':
            rows.append(f'<li><b>What was really going on, {e(cl.lower())}:</b> {e(fact)}</li>')
        else:
            real = fact.split('Real conditions to stay true to: ')[1].strip() if 'Real conditions to stay true to: ' in fact else ''
            body = (fact.split('. Use what is really true')[0] or how) + ', drawn from what is really happening around Peterborough this week.'
            if real:
                body += ' Held to the real weather: ' + real
            rows.append(f'<li><b>What was really going on, {e(cl.lower())}:</b> {e(body)}</li>')
    rows.append('<li><b>Your own day:</b> ' + ('yesterday\'s notes could shape it.' if pk.get('notes') else 'left out; the poem ignored the notes.') + '</li>')
    rows.append(f'<li><b>Memory:</b> it was shown the last {MEMORY} poems and told not to reuse their openings, images or endings.</li>')
    if a.spoken:
        import re
        def say(t):
            t = re.sub(r'Overnight lows this past week: [^;]*; ', '', t)
            t = re.sub(r'The past week brought 0\.00 in of rain in all\.', 'No rain at all this past week.', t)
            t = t.replace('°F', ' degrees').replace(' mph', ' miles an hour').replace('1 hard freezes', 'one hard freeze').replace(' (28 degrees or below)', '').replace(' frosts, ', ' frosts this past week, ')
            t = re.sub(r'Sunrise 0?(\d+):(\d\d), sunset (\d+):(\d\d)', lambda m: f'Sunrise at {int(m[1])}:{m[2]}, sunset at {int(m[3])-12}:{m[4]}', t)
            t = re.sub(r'(\d+) h (\d+) min', r'\1 hours \2 minutes', t)
            return t.strip()
        parts = [f'A note on how this poem was made. The way in was {lab.lower()}: {t.split(": ", 1)[-1]}.']
        named = []
        for k in pk.get('currents', []):
            cl, how = clab.get(k, (k, ''))
            fact = next((f[len(f'- {cl}: '):] for f in pk.get('facts', []) if f.startswith(f'- {cl}: ')), '')
            named.append(cl.lower())
            if how == 'live':
                fact = re.sub(r'^' + re.escape(cl) + r':\s*', '', fact)
                parts.append(f'On {cl.lower()}: {say(fact)}')
            elif 'Real conditions to stay true to: ' in fact:
                real = say(fact.split('Real conditions to stay true to: ')[1])
                parts.append(f'On {cl.lower()}, it was held to the real weather. {real}')
            else:
                h = re.sub(r'\s*\([^)]*\)', '', how)
                parts.append(f'For {cl.lower()}, it drew on {h}' + ('.' if 'this week' in h else ', true to this week around Peterborough.'))
        parts.insert(1, 'What was really going on came from ' + ' and '.join(named) + '.')
        parts.append('It could use your notes from yesterday.' if pk.get('notes') else 'It left your notes from yesterday out.')
        parts.append(f'And it was shown the last {MEMORY} poems and told not to repeat them.')
        print(' '.join(parts))
        return
    if a.technique:
        rows.append(f'<li><b>The lesson:</b> {e(a.technique.split(" — ")[0])}.</li>')
    print('<!--poem-made--><div class="poem-made" style="margin:-12px 0 24px;padding:14px 20px;border-left:3px solid #d8b25a;border-radius:10px;font-size:14px;line-height:1.6;color:var(--text-muted,#9a948a);">'
          '<div style="font-size:11px;letter-spacing:0.14em;text-transform:uppercase;margin-bottom:6px;">How this poem was made</div>'
          '<ul style="margin:0;padding-left:18px;">' + ''.join(rows) + '</ul>'
          '<div style="margin-top:6px;font-size:12px;">Pick the doors and currents at <a href="https://lists.benmartel.com/poem" style="color:#d8b25a;">lists.benmartel.com/poem</a>.</div></div><!--/poem-made-->')


def cmd_picks(a):
    doors, currents = load_picks()
    print(json.dumps({'doors': doors, 'currents': currents}, indent=1))


def cmd_page(a):
    import html as H
    def rows(items, group):
        out = []
        for k, lab, tell in items:
            sub = '' if tell in ('live', 'notes') else tell
            if group == 'doors':
                sub = tell
            elif tell == 'live':
                sub = 'live data each morning'
            elif tell == 'notes':
                sub = "the mood of yesterday's notes, as image only"
            out.append(f'<li class="ev" data-g="{group}" data-k="{k}"><button class="tick" aria-label="tick"><span class="sq"></span></button>'
                       f'<div><div class="nm">{H.escape(lab)}</div><div class="meta">{H.escape(sub[:1].upper() + sub[1:])}</div></div></li>')
        return '\n'.join(out)
    defaults = json.dumps({'doors': DOOR_DEFAULT, 'currents': CURRENT_DEFAULT})
    page = PAGE.replace('__DOORS__', rows(DOORS, 'doors')).replace('__CURRENTS__', rows(CURRENTS, 'currents')) \
               .replace('__DEFAULTS__', defaults).replace('__ND__', str(len(DOORS))).replace('__NC__', str(len(CURRENTS))) \
               .replace('__PER__', str(PER_MORNING)).replace('__MEM__', str(MEMORY))
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write(page)
    print('wrote', a.out)


PAGE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<title>Poem doors</title>
<style>
:root{--paper:#fff;--ink:#000;--line:#000;--font:"Helvetica Neue",Helvetica,Arial,sans-serif;--frame:3px}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--paper:#000;--ink:#fff;--line:#fff;color-scheme:dark}}
:root[data-theme="dark"]{--paper:#000;--ink:#fff;--line:#fff;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--font);font-size:16px;line-height:1.35}
.wrap{max-width:620px;margin:0 auto;padding:0 16px 64px;display:grid;grid-template-columns:minmax(0,1fr);gap:18px}
header.top{position:sticky;top:0;z-index:5;background:var(--ink);color:var(--paper);margin-inline:-16px;padding:12px 16px;display:flex;justify-content:space-between;align-items:center;gap:8px}
.top h1{margin:0;font-size:20px;font-weight:800;text-transform:uppercase;letter-spacing:.02em}
#st{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.06em}
.note{font-size:14px}
.box{border:var(--frame) solid var(--line)}
.box h2{margin:0;background:var(--ink);color:var(--paper);padding:7px 10px;font-size:14px;text-transform:uppercase;letter-spacing:.05em;display:flex;justify-content:space-between;gap:8px}
.box h2 span{font-weight:500;text-transform:none;letter-spacing:0}
ul{list-style:none;margin:0;padding:0}
.ev{display:grid;grid-template-columns:44px minmax(0,1fr);gap:8px;align-items:start;padding:9px 10px;border-top:1.5px solid var(--line);cursor:pointer}
.ev:first-child{border-top:0}
.tick{width:44px;height:44px;border:0;background:none;padding:0;cursor:pointer;display:grid;place-items:start center;color:var(--ink)}
.sq{width:28px;height:28px;border:var(--frame) solid var(--line);display:grid;place-items:center;margin-top:2px}
.ev.on .sq{background:var(--ink)}
.ev.on .sq::after{content:"";width:8px;height:15px;border:solid var(--paper);border-width:0 4px 4px 0;transform:translateY(-2px) rotate(45deg)}
.nm{font-weight:800;padding-top:6px}
.meta{font-size:13px}
.bar{display:flex;gap:8px;padding:8px 10px;border-top:1.5px solid var(--line)}
.bar button{font:inherit;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;background:var(--paper);color:var(--ink);border:2px solid var(--line);padding:6px 10px;cursor:pointer}
footer{font-size:12px}
</style></head><body>
<div class="wrap">
<header class="top"><h1>Poem doors</h1><span id="st">Saved</span></header>
<p class="note">Tick what the morning poem may use. Each morning takes <b>one door</b> (the way the poem walks in), choosing among the ticked doors you have heard least recently, and <b>__PER__ currents</b> (what is really going on in the world this week). It also remembers the last __MEM__ poems and avoids their images. Changes save as you tap and count from the next morning.</p>
<section class="box"><h2>Doors <span id="cd"></span></h2><ul>
__DOORS__
</ul><div class="bar"><button data-all="doors">Tick all</button><button data-none="doors">Clear</button></div></section>
<section class="box"><h2>Currents <span id="cc"></span></h2><ul>
__CURRENTS__
</ul><div class="bar"><button data-all="currents">Tick all</button><button data-none="currents">Clear</button></div></section>
<footer>A door you untick is never used. If every door is unticked, the original eight come back.</footer>
</div>
<script>
var S="__STATE__";var D=__DEFAULTS__;
if(!S||typeof S!=="object")S=D;if(!S.doors)S.doors=D.doors;if(!S.currents)S.currents=D.currents;
var st=document.getElementById("st");
function paint(){document.querySelectorAll(".ev").forEach(function(li){li.classList.toggle("on",S[li.dataset.g].indexOf(li.dataset.k)>=0)});
document.getElementById("cd").textContent=S.doors.length+" of __ND__";document.getElementById("cc").textContent=S.currents.length+" of __NC__"}
var t;function save(){st.textContent="Saving";clearTimeout(t);t=setTimeout(function(){
fetch(location.pathname.replace(/\/$/,"")+"/state",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(S),credentials:"same-origin"})
.then(function(r){st.textContent=r.ok?"Saved":"Not saved"}).catch(function(){st.textContent="Not saved"})},400)}
document.querySelectorAll(".ev").forEach(function(li){li.addEventListener("click",function(){var a=S[li.dataset.g],i=a.indexOf(li.dataset.k);if(i>=0)a.splice(i,1);else a.push(li.dataset.k);paint();save()})});
document.querySelectorAll("[data-all]").forEach(function(b){b.onclick=function(){var g=b.dataset.all;S[g]=[].map.call(document.querySelectorAll('.ev[data-g="'+g+'"]'),function(l){return l.dataset.k});paint();save()}});
document.querySelectorAll("[data-none]").forEach(function(b){b.onclick=function(){S[b.dataset.none]=[];paint();save()}});
paint();
</script></body></html>
'''


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('pick'); p.add_argument('--date', required=True); p.add_argument('--doorway'); p.add_argument('--out', required=True)
    p = sp.add_parser('record'); p.add_argument('--date', required=True); p.add_argument('--verse', required=True)
    p.add_argument('--motivator'); p.add_argument('--pick')
    p = sp.add_parser('page'); p.add_argument('--out', required=True)
    sp.add_parser('seed'); sp.add_parser('picks')
    p = sp.add_parser('made'); p.add_argument('--pick', required=True); p.add_argument('--technique'); p.add_argument('--spoken', action='store_true')
    a = ap.parse_args()
    {'pick': cmd_pick, 'record': cmd_record, 'page': cmd_page, 'seed': cmd_seed, 'picks': cmd_picks, 'made': cmd_made}[a.cmd](a)


if __name__ == '__main__':
    main()
