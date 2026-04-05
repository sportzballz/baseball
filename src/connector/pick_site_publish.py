import os
import re
import html
import json
import subprocess
from pathlib import Path
from datetime import datetime
import statsapi


SITE_BASE_URL = os.environ.get('SPORTZBALLZ_SITE_URL', 'https://sportzballz.io').rstrip('/')

ANALYST_PANEL = [
    {
        'id': 'joey-falcone',
        'name': 'Joey Falcone',
        'title': 'Stats & Vibes High-Roller',
        'voice': 'humorous, slick, Italian-American swagger, stat-nerd energy',
    },
    {
        'id': 'jimmy-the-grecian',
        'name': 'Jimmy the Grecian',
        'title': 'Vegas Insider',
        'voice': 'old-school bookmaker perspective, market discipline, veteran tone',
    },
    {
        'id': 'willie-guan',
        'name': 'Willie Guan',
        'title': 'Quant Mathematician',
        'voice': 'highly educated quantitative framing and probability-first language',
    },
    {
        'id': 'tommy-torrance',
        'name': 'Tommy Torrance',
        'title': 'Pragmatist (Gen X)',
        'voice': 'plainspoken, practical, Phillies-loving pragmatist: whatever works',
    },
]


def _site_url(path: str):
    p = path if path.startswith('/') else f'/{path}'
    return f"{SITE_BASE_URL}{p}"


def _render_robots_txt():
    return f"""User-agent: *
Allow: /

Sitemap: {_site_url('/sitemap.xml')}
"""


def _render_sitemap_xml(archive_dates):
    urls = [
        _site_url('/'),
        _site_url('/dashboard.html'),
        _site_url('/media-kit.html'),
        _site_url('/rate-card.html'),
    ]

    for d in sorted(set(archive_dates), reverse=True):
        urls.append(_site_url(f'/{d}.html'))
        urls.append(_site_url(f'/{d}-plus-money.html'))
        urls.append(_site_url(f'/{d}-run-totals.html'))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in urls:
        lines.append(f'  <url><loc>{html.escape(u)}</loc></url>')
    lines.append('</urlset>')
    return '\n'.join(lines)


def _render_ad_slot(slot_id: str, label: str, cta: str = '/media-kit.html'):
    return f'''<section class="ad-slot" data-slot="{html.escape(slot_id)}">
      <div class="ad-label">Sponsored</div>
      <div class="ad-copy">{html.escape(label)} • Your brand could be here.</div>
      <a class="ad-cta" href="{html.escape(cta)}">Advertise on SportzBallz</a>
    </section>'''


def _render_media_kit():
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SportzBallz | Media Kit</title>
  <meta name="description" content="SportzBallz media kit: audience, sponsorship inventory, and ad opportunities." />
  <meta name="robots" content="index,follow,max-image-preview:large" />
  <link rel="canonical" href="{_site_url('/media-kit.html')}" />
  <style>
    :root {{ --bg:#0b1020; --panel:#121c35; --ink:#e8efff; --muted:#9db1dc; --line:#2a3f72; --accent:#63d2ff; --accent2:#7cffc7; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:radial-gradient(1000px 650px at 10% -10%, #20356f, var(--bg)); color:var(--ink); font-family:Inter,system-ui,sans-serif; }}
    .wrap {{ max-width:980px; margin:0 auto; padding:24px 16px 48px; }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:16px; margin-bottom:14px; }}
    h1 {{ margin:0 0 8px; }} h2 {{ margin:0 0 10px; font-size:22px; }}
    .muted {{ color:var(--muted); }}
    ul {{ margin:8px 0 0 18px; }} li {{ margin:6px 0; }}
    .btn {{ display:inline-block; margin-right:8px; margin-top:8px; padding:8px 12px; border-radius:10px; text-decoration:none; color:#081224; background:linear-gradient(90deg,var(--accent),var(--accent2)); font-weight:700; }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="card">
      <h1>SportzBallz Media Kit</h1>
      <p class="muted">Daily MLB picks, plus-money cards, run-total leans, and performance tracking.</p>
      <a class="btn" href="/rate-card.html">View Rate Card</a>
      <a class="btn" href="/">Back to Homepage</a>
    </section>
    <section class="card"><h2>Audience & Format</h2><ul><li>MLB bettors seeking daily picks with structured context</li><li>Underdog/plus-money focused readers</li><li>Users who value transparent performance tracking</li></ul></section>
    <section class="card"><h2>Sponsorship Inventory</h2><ul><li>Homepage hero sponsor</li><li>Daily picks page sponsored placement</li><li>Plus money page sponsor</li><li>Run totals page sponsor</li><li>Dashboard sponsor</li></ul></section>
    <section class="card"><h2>Contact</h2><p>To sponsor SportzBallz, contact: <strong>ads@sportzballz.io</strong> (update as needed).</p></section>
  </main>
</body>
</html>
'''


def _render_rate_card():
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SportzBallz | Rate Card</title>
  <meta name="description" content="SportzBallz sponsorship pricing and ad package options." />
  <meta name="robots" content="index,follow,max-image-preview:large" />
  <link rel="canonical" href="{_site_url('/rate-card.html')}" />
  <style>
    :root {{ --bg:#0b1020; --panel:#121c35; --ink:#e8efff; --muted:#9db1dc; --line:#2a3f72; --accent:#63d2ff; --accent2:#7cffc7; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:radial-gradient(1000px 650px at 10% -10%, #20356f, var(--bg)); color:var(--ink); font-family:Inter,system-ui,sans-serif; }}
    .wrap {{ max-width:980px; margin:0 auto; padding:24px 16px 48px; }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:16px; margin-bottom:14px; }}
    table {{ width:100%; border-collapse:collapse; }} th, td {{ padding:10px 8px; border-bottom:1px solid #2a3f70; text-align:left; }}
    th {{ font-size:12px; text-transform:uppercase; letter-spacing:.08em; color:#cfe0ff; }}
    .muted {{ color:var(--muted); }}
    .btn {{ display:inline-block; margin-right:8px; margin-top:8px; padding:8px 12px; border-radius:10px; text-decoration:none; color:#081224; background:linear-gradient(90deg,var(--accent),var(--accent2)); font-weight:700; }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="card">
      <h1>SportzBallz Rate Card</h1>
      <p class="muted">Starter pricing — tune as traffic and conversion data matures.</p>
      <a class="btn" href="/media-kit.html">Media Kit</a><a class="btn" href="/">Homepage</a>
    </section>
    <section class="card">
      <table><thead><tr><th>Placement</th><th>Pricing</th><th>Notes</th></tr></thead><tbody>
        <tr><td>Homepage sponsor</td><td>$250–$750 / month</td><td>Prime brand placement on index.</td></tr>
        <tr><td>Daily picks sponsor</td><td>$150–$500 / month</td><td>Appears on core daily card pages.</td></tr>
        <tr><td>Plus-money sponsor</td><td>$125–$400 / month</td><td>Targets underdog/value readers.</td></tr>
        <tr><td>Run totals sponsor</td><td>$125–$400 / month</td><td>Targets totals-focused readers.</td></tr>
        <tr><td>Dashboard sponsor</td><td>$150–$500 / month</td><td>Performance page audience.</td></tr>
        <tr><td>Bundle package</td><td>$600–$1,500 / month</td><td>Index + daily + dashboard bundle.</td></tr>
      </tbody></table>
    </section>
  </main>
</body>
</html>
'''


def _parse_confidence(conf_text: str):
    if not conf_text:
        return None
    m = re.search(r'([0-9]+\.[0-9]+|[0-9]+)', conf_text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def _parse_data_points(conf_text: str):
    if not conf_text:
        return None
    m = re.search(r'data points:\s*(\d+)\/(\d+)', conf_text, re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _confidence_bucket(conf):
    if conf is None:
        return "unclear"
    if conf >= 0.45:
        return "high-conviction"
    if conf >= 0.25:
        return "solid"
    if conf >= 0.10:
        return "moderate"
    return "thin"


def _line_movement_note(text):
    t = (text or "").lower()
    if not t or "unavailable" in t:
        return "Market movement is limited in the feed, so this leans more on matchup signals than tape-reading the number."
    if "toward the pick side" in t:
        return "The market has drifted toward the pick side, which supports the model read but can compress value at the margin."
    if "away from the pick side" in t:
        return "The number has moved away from the pick side, which can improve price value if you trust the underlying edge."
    if "unchanged" in t:
        return "The line has held steady, suggesting a relatively stable market view into first pitch."
    return f"Line context: {text}"


def _total_odds_pick(total_line_text):
    # expected: "8 (Over -115 / Under -105)"
    if not total_line_text:
        return None, None, None
    m = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*\(Over\s*([+-]?\d+|—)\s*/\s*Under\s*([+-]?\d+|—)\)', total_line_text)
    if not m:
        return None, None, None
    total = float(m.group(1))
    over_odds = None if m.group(2) == '—' else int(m.group(2))
    under_odds = None if m.group(3) == '—' else int(m.group(3))
    return total, over_odds, under_odds


def _run_total_lean(pick):
    winner, loser = pick['winner'], pick['loser']
    weather = _field(pick, 'Weather', '')
    venue = _field(pick, 'Venue', '')
    w_sig = _field(pick, f'{winner} Model Signals', '')
    l_sig = _field(pick, f'{loser} Model Signals', '')
    total_line_text = _field(pick, 'Total Line', '')
    total_move_text = _field(pick, 'Total Movement', '')

    total, over_odds, under_odds = _total_odds_pick(total_line_text)
    if total is None:
        return None

    sig_text = f"{w_sig}, {l_sig}".lower()
    over_score = 0
    under_score = 0
    reasons = []

    # Weather heuristics
    w = weather.lower()
    if 'dome' in w or 'roof' in w:
        reasons.append('roof-controlled environment')
    wind_m = re.search(r'(\d+)\s*mph', w)
    wind = int(wind_m.group(1)) if wind_m else 0
    if 'out to' in w and wind >= 10:
        over_score += 2
        reasons.append('wind blowing out')
    if 'in from' in w and wind >= 10:
        under_score += 2
        reasons.append('wind blowing in')

    temp_m = re.search(r'(\d+)°f', w)
    temp = int(temp_m.group(1)) if temp_m else None
    if temp is not None and temp >= 78:
        over_score += 1
        reasons.append('warm run environment')
    if temp is not None and temp <= 52:
        under_score += 1
        reasons.append('cool run environment')
    if 'rain' in w:
        under_score += 1
        reasons.append('rain suppression risk')

    # Signal heuristics (internal only, not exposing raw names)
    over_terms = ['runs', 'homeruns', 'doubles', 'triples', 'rbi', 'runsscoredper9', 'homerunsper9', 'batters have most runs', 'batters have most home runs']
    under_terms = ['era', 'whip', 'strikeoutsper9', 'strikepercentage', 'pitcher has fewer runs', 'pitcher has fewer earned runs', 'pitcher has fewer home runs']

    over_hits = sum(1 for t in over_terms if t in sig_text)
    under_hits = sum(1 for t in under_terms if t in sig_text)
    if over_hits > under_hits:
        over_score += 1
        reasons.append('offensive indicator edge')
    elif under_hits > over_hits:
        under_score += 1
        reasons.append('run-prevention indicator edge')

    # Market nudge
    tm = total_move_text.lower()
    if 'moved up' in tm:
        over_score += 1
        reasons.append('market moved total up')
    elif 'moved down' in tm:
        under_score += 1
        reasons.append('market moved total down')

    if over_score == under_score:
        side = 'OVER' if (over_odds or 0) >= (under_odds or 0) else 'UNDER'
    else:
        side = 'OVER' if over_score > under_score else 'UNDER'

    conf_text = _field(pick, 'Model Confidence', '0')
    conf = _parse_confidence(conf_text) or 0
    edge = abs(over_score - under_score)
    total_conf = round((edge * 0.15) + (conf * 0.35), 3)

    return {
        'winner': winner,
        'loser': loser,
        'venue': venue,
        'pick': side,
        'line': total,
        'over_odds': over_odds,
        'under_odds': under_odds,
        'confidence': total_conf,
        'weather': weather,
        'total_movement': total_move_text,
        'reasons': reasons[:4],
    }


def _weather_note(venue, weather):
    w = weather or ""
    if "dome/retractable roof" in w.lower() or "not applicable" in w.lower():
        return f"At {venue}, roof conditions mute weather volatility, keeping this matchup more talent-and-execution driven."

    wind_match = re.search(r'(\d+)\s*mph', w.lower())
    wind = int(wind_match.group(1)) if wind_match else None
    if wind and wind >= 12:
        return f"Weather is a real variable here ({weather}); that wind profile can materially influence run environment and ball carry."
    if w and "unavailable" not in w.lower():
        return f"Conditions at {venue} ({weather}) are worth tracking, but they don’t look extreme enough to override core matchup factors."
    return f"Weather detail is limited from {venue}, so this reads primarily through pitcher profile, lineup edge, and market context."


def _injury_note(winner, loser, winner_inj, loser_inj):
    def cnt(txt):
        if not txt or txt.lower().startswith('n/a'):
            return 0
        return max(1, txt.count(',') + 1)

    w = cnt(winner_inj)
    l = cnt(loser_inj)
    if w == 0 and l == 0:
        return "Injury reporting is light in this feed, so availability risk appears neutral on both sides."
    if l - w >= 2:
        return f"Availability leans slightly toward {winner}; {loser} is carrying a heavier listed injury load."
    if w - l >= 2:
        return f"Injury depth leans against {winner}, so this position depends more heavily on matchup execution than roster health."
    return "Injury load looks relatively balanced, so this projects as a baseball-context and pricing decision more than a health fade."


def _umpire_note(ump):
    if not ump or "unavailable" in ump.lower():
        return "Umpire assignment is unclear at publish time, so plate-profile impact remains a late variable."
    hp = None
    for part in ump.split(';'):
        p = part.strip()
        if p.lower().startswith('home plate:'):
            hp = p.split(':', 1)[1].strip()
            break
    if hp:
        return f"Home plate assignment ({hp}) is in place, which sharp bettors will monitor for zone tendencies once game action starts."
    return f"Crew assignment is posted ({ump}), adding context for in-game strike-zone texture and pace."


def _parse_markdown(md_text: str):
    lines = md_text.splitlines()
    date_str = ""
    model = "dutch"
    picks = []
    current = None

    for line in lines:
        if line.startswith('# MLB Picks Commentary — '):
            date_str = line.split('—', 1)[1].strip()
            continue

        if line.startswith('- Model: '):
            m = re.search(r'`([^`]+)`', line)
            model = m.group(1) if m else line.split(':', 1)[1].strip()
            continue

        if line.startswith('## '):
            if current:
                picks.append(current)
            title = line[3:].strip()
            m = re.match(r'\d+\)\s+(.*?)\s+over\s+(.*)$', title)
            current = {
                'winner': m.group(1).strip() if m else title,
                'loser': m.group(2).strip() if m else '',
                'fields': {},
            }
            continue

        if current:
            # markdown format currently: - **Pick Odds:** -109
            m1 = re.match(r'^- \*\*(.+?):\*\*\s*(.*)$', line)
            if m1:
                current['fields'][m1.group(1).strip()] = m1.group(2).strip()
                continue

            # fallback format: - **Pick Odds**: -109
            m2 = re.match(r'^- \*\*(.+?)\*\*:\s*(.*)$', line)
            if m2:
                current['fields'][m2.group(1).strip()] = m2.group(2).strip()
                continue

    if current:
        picks.append(current)

    return {
        'date': date_str,
        'model': model,
        'picks': picks,
    }


def _field(pick, key, default='n/a'):
    return pick['fields'].get(key, default)


def _odds_value(odds_text: str):
    if not odds_text:
        return None
    t = str(odds_text).strip()
    if t in ('----', 'n/a', 'N/A'):
        return None
    try:
        return int(t)
    except Exception:
        m = re.search(r'([+-]?\d+)', t)
        if not m:
            return None


def _safe_int(v):
    try:
        return int(v)
    except Exception:
        return None


def _build_matchup_games(game_date: str):
    games = statsapi.schedule(start_date=game_date, end_date=game_date)
    matchups = {}
    for g in games:
        home = g.get('home_name')
        away = g.get('away_name')
        if not home or not away:
            continue
        key = tuple(sorted([home, away]))

        home_score = _safe_int(g.get('home_score'))
        away_score = _safe_int(g.get('away_score'))
        status = str(g.get('status', ''))
        is_final = 'final' in status.lower()

        winner = g.get('winning_team')
        if not winner and is_final and home_score is not None and away_score is not None:
            winner = home if home_score > away_score else away

        matchups.setdefault(key, []).append({
            'status': status,
            'is_final': is_final,
            'winner': winner,
            'game_datetime': g.get('game_datetime') or '',
            'home': home,
            'away': away,
            'home_score': home_score,
            'away_score': away_score,
        })

    # keep deterministic order for doubleheaders
    for key in matchups:
        matchups[key].sort(key=lambda x: x.get('game_datetime', ''))

    return matchups


def _evaluate_picks(parsed):
    matchups = _build_matchup_games(parsed['date'])
    seen_idx = {}
    evaluated = []

    for p in parsed['picks']:
        winner = p['winner']
        loser = p['loser']
        key = tuple(sorted([winner, loser]))
        idx = seen_idx.get(key, 0)
        seen_idx[key] = idx + 1

        games = matchups.get(key, [])
        game = games[idx] if idx < len(games) else None

        result = 'PENDING'
        status = 'Not found'
        actual_winner = None

        if game:
            status = game.get('status', 'Unknown')
            actual_winner = game.get('winner')
            if game.get('is_final') and actual_winner:
                result = 'WIN' if actual_winner == winner else 'LOSS'
            elif game.get('is_final') and not actual_winner:
                result = 'UNKNOWN'

        ev = dict(p)
        ev['result'] = result
        ev['game_status'] = status
        ev['actual_winner'] = actual_winner
        evaluated.append(ev)

    decided = [x for x in evaluated if x['result'] in ('WIN', 'LOSS')]
    wins = len([x for x in decided if x['result'] == 'WIN'])
    losses = len([x for x in decided if x['result'] == 'LOSS'])
    pending = len([x for x in evaluated if x['result'] == 'PENDING'])

    plus = [x for x in evaluated if (_odds_value(_field(x, 'Pick Odds', '')) or -99999) > 0]
    plus_decided = [x for x in plus if x['result'] in ('WIN', 'LOSS')]
    plus_wins = len([x for x in plus_decided if x['result'] == 'WIN'])
    plus_losses = len([x for x in plus_decided if x['result'] == 'LOSS'])

    summary = {
        'date': parsed['date'],
        'total_picks': len(evaluated),
        'decided': len(decided),
        'wins': wins,
        'losses': losses,
        'pending': pending,
        'win_rate': round((wins / len(decided)) * 100, 1) if decided else None,
        'plus_money_total': len(plus),
        'plus_money_decided': len(plus_decided),
        'plus_money_wins': plus_wins,
        'plus_money_losses': plus_losses,
        'plus_money_win_rate': round((plus_wins / len(plus_decided)) * 100, 1) if plus_decided else None,
    }

    return evaluated, summary


def _render_tracker_block(summary):
    wr = f"{summary['win_rate']}%" if summary['win_rate'] is not None else "—"
    pwr = f"{summary['plus_money_win_rate']}%" if summary['plus_money_win_rate'] is not None else "—"
    return f'''
    <section class="tracker">
      <div class="tracker-grid">
        <div class="tcard"><span>Total Picks</span><strong>{summary['total_picks']}</strong></div>
        <div class="tcard"><span>Decided</span><strong>{summary['decided']}</strong></div>
        <div class="tcard"><span>Record</span><strong>{summary['wins']}-{summary['losses']}</strong></div>
        <div class="tcard"><span>Win Rate</span><strong>{wr}</strong></div>
        <div class="tcard"><span>Plus Money Record</span><strong>{summary['plus_money_wins']}-{summary['plus_money_losses']}</strong></div>
        <div class="tcard"><span>Plus Money Win %</span><strong>{pwr}</strong></div>
      </div>
    </section>
    '''


def _analysis_paragraph(pick, idx):
    winner, loser = pick['winner'], pick['loser']
    conf_text = _field(pick, 'Model Confidence', 'n/a')
    conf = _parse_confidence(conf_text)
    dp = _parse_data_points(conf_text)
    dp_text = f"{dp[0]}/{dp[1]}" if dp else "n/a"
    bucket = _confidence_bucket(conf)

    odds = _field(pick, 'Pick Odds', '----')
    pitching = _field(pick, 'Pitching Matchup', 'n/a')
    venue = _field(pick, 'Venue', 'n/a')
    weather = _field(pick, 'Weather', 'n/a')
    ump = _field(pick, 'Umpire Crew', 'n/a')
    line_move = _field(pick, 'Line Movement', 'n/a')
    w_sig = _field(pick, f'{winner} Model Signals', 'n/a')
    l_sig = _field(pick, f'{loser} Model Signals', 'n/a')
    w_sig_count = 0 if not w_sig or w_sig == 'n/a' else len([s for s in w_sig.split(',') if s.strip()])
    l_sig_count = 0 if not l_sig or l_sig == 'n/a' else len([s for s in l_sig.split(',') if s.strip()])
    w_inj = _field(pick, f'{winner} Injuries', 'n/a')
    l_inj = _field(pick, f'{loser} Injuries', 'n/a')

    analyst = ANALYST_PANEL[(idx - 1) % len(ANALYST_PANEL)]

    voices = {
        'joey-falcone': (
            "Joey’s angle:",
            f"{winner} over {loser} is the kind of {bucket} ticket you slide across the counter with a grin. Price is {odds}, confidence is {conf_text}, "
            f"and the stat split ({dp_text}) says this isn’t just sauce. On the nerd side, {winner} shows the stronger indicator stack "
            f"({w_sig_count} to {l_sig_count}) with {pitching} setting the first chapter."
        ),
        'jimmy-the-grecian': (
            "Jimmy’s book:",
            f"{winner} over {loser} grades as a {bucket} play at {odds}. Confidence sits at {conf_text} with a {dp_text} profile, and the edge starts with "
            f"{pitching}. This is less about headlines and more about taking a number where the baseball and the market still agree enough to fire."
        ),
        'willie-guan': (
            "Willie’s model note:",
            f"For {winner} over {loser}, the confidence estimate ({conf_text}) and signal distribution ({dp_text}) imply a {bucket} probability edge at {odds}. "
            f"Pitch-level context ({pitching}) plus indicator asymmetry ({w_sig_count} vs {l_sig_count}) supports positive expected value under current pricing."
        ),
        'tommy-torrance': (
            "Tommy’s take:",
            f"{winner} over {loser}. Keep it simple: {conf_text}, line at {odds}, and {pitching} gives this spot a workable shape. "
            f"It’s a {bucket} look with enough signal separation ({w_sig_count}-{l_sig_count}) to back the play without overthinking it."
        ),
    }

    prefix, lead = voices.get(analyst['id'], next(iter(voices.values())))
    return (
        f"{analyst['name']} ({analyst['title']}) — {prefix} {lead} "
        f"{_weather_note(venue, weather)} "
        f"{_umpire_note(ump)} "
        f"{_injury_note(winner, loser, w_inj, l_inj)} "
        f"{_line_movement_note(line_move)}"
    )


def _render_daily_html(parsed, evaluated_picks=None, summary=None):
    picks_source = evaluated_picks if evaluated_picks is not None else parsed['picks']
    picks = sorted(
        picks_source,
        key=lambda p: _parse_confidence(_field(p, 'Model Confidence', '')) or -1,
        reverse=True,
    )
    date_str = parsed['date']
    model = parsed['model']
    now = datetime.now().strftime('%Y-%m-%d %I:%M %p')

    cards = []
    for i, p in enumerate(picks, 1):
        winner, loser = p['winner'], p['loser']
        result = p.get('result', 'PENDING')
        result_class = 'res-pending'
        if result == 'WIN':
            result_class = 'res-win'
        elif result == 'LOSS':
            result_class = 'res-loss'
        cards.append(f'''
      <article class="pick-card">
        <div class="pick-head">
          <div class="pick-num">Pick {i}</div>
          <h2>{html.escape(winner)} over {html.escape(loser)}</h2>
          <span class="res {result_class}">{result}</span>
        </div>
        <div class="meta-grid">
          <div><span>Odds</span><strong>{html.escape(_field(p,'Pick Odds','----'))}</strong></div>
          <div><span>Confidence</span><strong>{html.escape(_field(p,'Model Confidence','n/a'))}</strong></div>
          <div><span>Pitching</span><strong>{html.escape(_field(p,'Pitching Matchup','n/a'))}</strong></div>
          <div><span>Venue</span><strong>{html.escape(_field(p,'Venue','n/a'))}</strong></div>
        </div>
        <p class="lede">{_analysis_paragraph(p, i)}</p>
        <details>
          <summary>Expanded game context</summary>
          <ul>
            <li><strong>Weather:</strong> {html.escape(_field(p,'Weather','n/a'))}</li>
            <li><strong>Umpire Crew:</strong> {html.escape(_field(p,'Umpire Crew','n/a'))}</li>
            <li><strong>{html.escape(winner)} Injuries:</strong> {html.escape(_field(p,f'{winner} Injuries','n/a'))}</li>
            <li><strong>{html.escape(loser)} Injuries:</strong> {html.escape(_field(p,f'{loser} Injuries','n/a'))}</li>
            <li><strong>Line Movement:</strong> {html.escape(_field(p,'Line Movement','n/a'))}</li>
          </ul>
        </details>
      </article>
    ''')

    tracker_html = _render_tracker_block(summary) if summary else ''

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SportzBallz | MLB Daily Notebook</title>
  <meta name="description" content="Warm, insider-style MLB daily pick commentary from SportzBallz." />
  <meta name="robots" content="index,follow,max-image-preview:large" />
  <link rel="canonical" href="{_site_url('/' + date_str + '.html')}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="SportzBallz" />
  <meta property="og:title" content="SportzBallz MLB Picks — {html.escape(date_str)}" />
  <meta property="og:description" content="Daily MLB picks with confidence, pricing context, plus-money and run-total analysis." />
  <meta property="og:url" content="{_site_url('/' + date_str + '.html')}" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="SportzBallz MLB Picks — {html.escape(date_str)}" />
  <meta name="twitter:description" content="Daily MLB picks with confidence, pricing context, plus-money and run-total analysis." />
  <style>
    :root {{ --bg:#0a1020; --panel:#101a33; --ink:#eaf0ff; --muted:#a7b7df; --line:#273a6b; --accent:#5cc9ff; --accent2:#88f2c7; }}
    *{{box-sizing:border-box}}
    body{{margin:0;font-family:Georgia,'Times New Roman',serif;background:radial-gradient(1200px 700px at 15% -10%, #1a2a55, var(--bg));color:var(--ink);line-height:1.65}}
    .wrap{{max-width:1100px;margin:0 auto;padding:24px 16px 48px}}
    header{{background:linear-gradient(135deg, rgba(92,201,255,.18), rgba(136,242,199,.09));border:1px solid var(--line);border-radius:16px;padding:22px;margin-bottom:16px}}
    .kicker{{font:600 12px/1.2 Inter,system-ui,sans-serif;letter-spacing:.12em;color:var(--muted);text-transform:uppercase}}
    h1{{margin:8px 0 10px;font-size:clamp(30px,5vw,46px);line-height:1.05}}
    .sub{{color:var(--muted);font-family:Inter,system-ui,sans-serif;font-size:14px}}
    .intro{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-bottom:16px;font-size:18px}}
    .ad-slot{{background:rgba(255,255,255,.03);border:1px dashed #3b5a96;border-radius:12px;padding:12px 14px;margin:0 0 14px 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
    .ad-label{{font:700 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.08em;color:#9cc4ff}}
    .ad-copy{{color:#d9e6ff;font:500 14px/1.3 Inter,system-ui,sans-serif}}
    .ad-cta{{display:inline-block;padding:7px 10px;border-radius:8px;border:1px solid #4c6db0;color:#dff2ff;text-decoration:none;font:600 12px Inter,system-ui,sans-serif}}
    .pick-card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:0 0 14px 0;box-shadow:0 12px 28px rgba(0,0,0,.24)}}
    .pick-head h2{{margin:4px 0 8px;font-size:30px;line-height:1.15}}
    .pick-head{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
    .pick-num{{font:600 12px/1 Inter,system-ui,sans-serif;color:var(--accent);letter-spacing:.12em;text-transform:uppercase}}
    .res{{font:700 11px/1 Inter,system-ui,sans-serif;padding:5px 8px;border-radius:999px;border:1px solid #31508e;}}
    .res-win{{color:#7CFFB3;border-color:#2f8f57;background:rgba(52,211,153,.12)}}
    .res-loss{{color:#ff9ca0;border-color:#a13d47;background:rgba(239,68,68,.14)}}
    .res-pending{{color:#cfe1ff;border-color:#3c5c97;background:rgba(59,130,246,.12)}}
    .tracker{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin-bottom:16px}}
    .tracker-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}}
    .tcard{{border:1px dashed #31508e;border-radius:10px;padding:8px 10px;background:rgba(255,255,255,.02)}}
    .tcard span{{display:block;color:var(--muted);font:600 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px}}
    .tcard strong{{font:700 16px/1.25 Inter,system-ui,sans-serif;color:#e7f0ff}}
    .meta-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px 12px;padding:10px 0 2px}}
    .meta-grid div{{border:1px dashed #31508e;border-radius:10px;padding:8px 10px;background:rgba(255,255,255,.02)}}
    .meta-grid span{{display:block;color:var(--muted);font:600 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px}}
    .meta-grid strong{{font:600 15px/1.35 Inter,system-ui,sans-serif;color:#dce8ff}}
    .lede{{font-size:20px;margin:12px 0 8px;color:#f2f6ff}}
    details{{margin-top:8px;border-top:1px solid #264377;padding-top:8px}}
    summary{{cursor:pointer;font:600 14px Inter,system-ui,sans-serif;color:var(--accent)}}
    ul{{margin:10px 0 0 18px;padding:0}}
    li{{margin:6px 0}}
    footer{{margin-top:10px;color:var(--muted);font:12px Inter,system-ui,sans-serif;text-align:right}}
    @media (max-width:720px){{.lede{{font-size:18px}} .pick-head h2{{font-size:24px}}}}
  </style>
</head>
<body>
  <main class="wrap">
    <header>
      <div class="kicker">SportzBallz Daily Desk</div>
      <h1>MLB Daily Notebook — {html.escape(date_str)}</h1>
      <div class="sub">Model: {html.escape(model)} • Updated {html.escape(now)}</div>
    </header>
    <section class="intro">Today’s card in a warmer, notebook-style voice — balancing matchup context, weather, umpire texture, and price discipline.</section>
    {_render_ad_slot('daily-top', 'Daily Notebook Sponsorship')}
    {tracker_html}
    {''.join(cards)}
    <footer>Published by SportzBallz.io</footer>
  </main>
</body>
</html>
'''


def _render_plus_money_html(parsed, evaluated_picks=None, summary=None):
    source = evaluated_picks if evaluated_picks is not None else parsed['picks']
    all_picks = sorted(
        source,
        key=lambda p: _parse_confidence(_field(p, 'Model Confidence', '')) or -1,
        reverse=True,
    )
    plus_picks = []
    for p in all_picks:
        ov = _odds_value(_field(p, 'Pick Odds', ''))
        if ov is not None and ov > 0:
            plus_picks.append(p)

    date_str = parsed['date']
    model = parsed['model']
    now = datetime.now().strftime('%Y-%m-%d %I:%M %p')

    cards = []
    for i, p in enumerate(plus_picks, 1):
        winner, loser = p['winner'], p['loser']
        result = p.get('result', 'PENDING')
        result_class = 'res-pending'
        if result == 'WIN':
            result_class = 'res-win'
        elif result == 'LOSS':
            result_class = 'res-loss'
        cards.append(f'''
      <article class="pick-card">
        <div class="pick-head">
          <div class="pick-num">Underdog {i}</div>
          <h2>{html.escape(winner)} over {html.escape(loser)}</h2>
          <span class="res {result_class}">{result}</span>
        </div>
        <div class="meta-grid">
          <div><span>Odds</span><strong>{html.escape(_field(p,'Pick Odds','----'))}</strong></div>
          <div><span>Confidence</span><strong>{html.escape(_field(p,'Model Confidence','n/a'))}</strong></div>
          <div><span>Pitching</span><strong>{html.escape(_field(p,'Pitching Matchup','n/a'))}</strong></div>
          <div><span>Venue</span><strong>{html.escape(_field(p,'Venue','n/a'))}</strong></div>
        </div>
        <p class="lede">{_analysis_paragraph(p, i)}</p>
        <details>
          <summary>Expanded game context</summary>
          <ul>
            <li><strong>Weather:</strong> {html.escape(_field(p,'Weather','n/a'))}</li>
            <li><strong>Umpire Crew:</strong> {html.escape(_field(p,'Umpire Crew','n/a'))}</li>
            <li><strong>{html.escape(winner)} Injuries:</strong> {html.escape(_field(p,f'{winner} Injuries','n/a'))}</li>
            <li><strong>{html.escape(loser)} Injuries:</strong> {html.escape(_field(p,f'{loser} Injuries','n/a'))}</li>
            <li><strong>Line Movement:</strong> {html.escape(_field(p,'Line Movement','n/a'))}</li>
          </ul>
        </details>
      </article>
    ''')

    if not cards:
        cards.append(
            '<article class="pick-card"><h2>No Plus Money Picks Today</h2><p class="lede">No underdog selections met publication criteria for this slate.</p></article>'
        )

    pm_summary_html = ''
    if summary:
        pwr = f"{summary['plus_money_win_rate']}%" if summary['plus_money_win_rate'] is not None else "—"
        pm_summary_html = f'''
        <section class="tracker">
          <div class="tracker-grid">
            <div class="tcard"><span>Plus Money Picks</span><strong>{summary['plus_money_total']}</strong></div>
            <div class="tcard"><span>Decided</span><strong>{summary['plus_money_decided']}</strong></div>
            <div class="tcard"><span>Record</span><strong>{summary['plus_money_wins']}-{summary['plus_money_losses']}</strong></div>
            <div class="tcard"><span>Win Rate</span><strong>{pwr}</strong></div>
          </div>
        </section>
        '''

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SportzBallz | Plus Money Picks</title>
  <meta name="description" content="SportzBallz underdog MLB picks for {html.escape(date_str)}." />
  <meta name="robots" content="index,follow,max-image-preview:large" />
  <link rel="canonical" href="{_site_url('/' + date_str + '-plus-money.html')}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="SportzBallz" />
  <meta property="og:title" content="SportzBallz Plus Money Picks — {html.escape(date_str)}" />
  <meta property="og:description" content="Underdog-only MLB picks with confidence and matchup context." />
  <meta property="og:url" content="{_site_url('/' + date_str + '-plus-money.html')}" />
  <meta name="twitter:card" content="summary_large_image" />
  <style>
    :root {{ --bg:#0a1020; --panel:#101a33; --ink:#eaf0ff; --muted:#a7b7df; --line:#273a6b; --accent:#5cc9ff; --accent2:#88f2c7; --plus:#22c55e; }}
    *{{box-sizing:border-box}}
    body{{margin:0;font-family:Georgia,'Times New Roman',serif;background:radial-gradient(1200px 700px at 15% -10%, #1a2a55, var(--bg));color:var(--ink);line-height:1.65}}
    .wrap{{max-width:1100px;margin:0 auto;padding:24px 16px 48px}}
    header{{background:linear-gradient(135deg, rgba(34,197,94,.20), rgba(92,201,255,.10));border:1px solid var(--line);border-radius:16px;padding:22px;margin-bottom:16px}}
    .kicker{{font:600 12px/1.2 Inter,system-ui,sans-serif;letter-spacing:.12em;color:var(--muted);text-transform:uppercase}}
    h1{{margin:8px 0 10px;font-size:clamp(30px,5vw,46px);line-height:1.05}}
    .sub{{color:var(--muted);font-family:Inter,system-ui,sans-serif;font-size:14px}}
    .intro{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-bottom:16px;font-size:18px}}
    .ad-slot{{background:rgba(255,255,255,.03);border:1px dashed #3b5a96;border-radius:12px;padding:12px 14px;margin:0 0 14px 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
    .ad-label{{font:700 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.08em;color:#9cc4ff}}
    .ad-copy{{color:#d9e6ff;font:500 14px/1.3 Inter,system-ui,sans-serif}}
    .ad-cta{{display:inline-block;padding:7px 10px;border-radius:8px;border:1px solid #4c6db0;color:#dff2ff;text-decoration:none;font:600 12px Inter,system-ui,sans-serif}}
    .pick-card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:0 0 14px 0;box-shadow:0 12px 28px rgba(0,0,0,.24)}}
    .pick-head h2{{margin:4px 0 8px;font-size:30px;line-height:1.15}}
    .pick-head{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
    .pick-num{{font:600 12px/1 Inter,system-ui,sans-serif;color:var(--plus);letter-spacing:.12em;text-transform:uppercase}}
    .res{{font:700 11px/1 Inter,system-ui,sans-serif;padding:5px 8px;border-radius:999px;border:1px solid #31508e;}}
    .res-win{{color:#7CFFB3;border-color:#2f8f57;background:rgba(52,211,153,.12)}}
    .res-loss{{color:#ff9ca0;border-color:#a13d47;background:rgba(239,68,68,.14)}}
    .res-pending{{color:#cfe1ff;border-color:#3c5c97;background:rgba(59,130,246,.12)}}
    .tracker{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin-bottom:16px}}
    .tracker-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}}
    .tcard{{border:1px dashed #31508e;border-radius:10px;padding:8px 10px;background:rgba(255,255,255,.02)}}
    .tcard span{{display:block;color:var(--muted);font:600 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px}}
    .tcard strong{{font:700 16px/1.25 Inter,system-ui,sans-serif;color:#e7f0ff}}
    .meta-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px 12px;padding:10px 0 2px}}
    .meta-grid div{{border:1px dashed #31508e;border-radius:10px;padding:8px 10px;background:rgba(255,255,255,.02)}}
    .meta-grid span{{display:block;color:var(--muted);font:600 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px}}
    .meta-grid strong{{font:600 15px/1.35 Inter,system-ui,sans-serif;color:#dce8ff}}
    .lede{{font-size:20px;margin:12px 0 8px;color:#f2f6ff}}
    details{{margin-top:8px;border-top:1px solid #264377;padding-top:8px}}
    summary{{cursor:pointer;font:600 14px Inter,system-ui,sans-serif;color:var(--accent)}}
    ul{{margin:10px 0 0 18px;padding:0}}
    li{{margin:6px 0}}
    .toplinks{{display:flex;gap:10px;margin-top:10px;flex-wrap:wrap}}
    .toplinks a{{display:inline-block;padding:8px 12px;border:1px solid #31508e;border-radius:9px;color:#dce8ff;text-decoration:none;font-family:Inter,system-ui,sans-serif;font-size:13px}}
    footer{{margin-top:10px;color:var(--muted);font:12px Inter,system-ui,sans-serif;text-align:right}}
    @media (max-width:720px){{.lede{{font-size:18px}} .pick-head h2{{font-size:24px}}}}
  </style>
</head>
<body>
  <main class="wrap">
    <header>
      <div class="kicker">SportzBallz Plus Money Desk</div>
      <h1>Plus Money Picks — {html.escape(date_str)}</h1>
      <div class="sub">Model: {html.escape(model)} • Updated {html.escape(now)}</div>
      <div class="toplinks">
        <a href="/{html.escape(date_str)}.html">Full Daily Picks</a>
        <a href="/">Home</a>
      </div>
    </header>
    <section class="intro">All underdog selections (positive odds) for the day, ordered by confidence.</section>
    {_render_ad_slot('plus-money-top', 'Plus Money Card Sponsorship')}
    {pm_summary_html}
    {''.join(cards)}
    <footer>Published by SportzBallz.io</footer>
  </main>
</body>
</html>
'''


def _render_run_totals_html(parsed, evaluated_picks=None):
    source = evaluated_picks if evaluated_picks is not None else parsed['picks']
    leans = []
    for p in source:
        lean = _run_total_lean(p)
        if lean:
            leans.append(lean)

    leans.sort(key=lambda x: x['confidence'], reverse=True)

    date_str = parsed['date']
    model = parsed['model']
    now = datetime.now().strftime('%Y-%m-%d %I:%M %p')

    cards = []
    for i, l in enumerate(leans, 1):
        price = l['over_odds'] if l['pick'] == 'OVER' else l['under_odds']
        cards.append(f'''
      <article class="pick-card">
        <div class="pick-head">
          <div class="pick-num">Run Total {i}</div>
          <h2>{html.escape(l['winner'])} vs {html.escape(l['loser'])} — {l['pick']} {l['line']}</h2>
        </div>
        <div class="meta-grid">
          <div><span>Lean</span><strong>{l['pick']} {l['line']}</strong></div>
          <div><span>Price</span><strong>{price if price is not None else '—'}</strong></div>
          <div><span>Confidence</span><strong>{l['confidence']}</strong></div>
          <div><span>Venue</span><strong>{html.escape(l['venue'])}</strong></div>
        </div>
        <p class="lede">Run-total lens: {l['pick']} {l['line']} in {l['winner']} vs {l['loser']}. Supporting context includes {', '.join(l['reasons']) if l['reasons'] else 'balanced conditions and market context'}.</p>
        <details>
          <summary>Expanded total context</summary>
          <ul>
            <li><strong>Weather:</strong> {html.escape(l['weather'])}</li>
            <li><strong>Total Movement:</strong> {html.escape(l['total_movement'])}</li>
          </ul>
        </details>
      </article>
    ''')

    if not cards:
        cards.append('<article class="pick-card"><h2>No Run Total Leans Today</h2><p class="lede">Total-line data unavailable for today’s slate.</p></article>')

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SportzBallz | Run Total Picks</title>
  <meta name="description" content="SportzBallz MLB run total picks for {html.escape(date_str)}." />
  <meta name="robots" content="index,follow,max-image-preview:large" />
  <link rel="canonical" href="{_site_url('/' + date_str + '-run-totals.html')}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="SportzBallz" />
  <meta property="og:title" content="SportzBallz Run Total Picks — {html.escape(date_str)}" />
  <meta property="og:description" content="MLB totals leans built from confidence, pricing, weather and movement context." />
  <meta property="og:url" content="{_site_url('/' + date_str + '-run-totals.html')}" />
  <meta name="twitter:card" content="summary_large_image" />
  <style>
    :root {{ --bg:#0a1020; --panel:#101a33; --ink:#eaf0ff; --muted:#a7b7df; --line:#273a6b; --accent:#f59e0b; --accent2:#5cc9ff; }}
    *{{box-sizing:border-box}}
    body{{margin:0;font-family:Georgia,'Times New Roman',serif;background:radial-gradient(1200px 700px at 15% -10%, #1a2a55, var(--bg));color:var(--ink);line-height:1.65}}
    .wrap{{max-width:1100px;margin:0 auto;padding:24px 16px 48px}}
    header{{background:linear-gradient(135deg, rgba(245,158,11,.20), rgba(92,201,255,.10));border:1px solid var(--line);border-radius:16px;padding:22px;margin-bottom:16px}}
    .kicker{{font:600 12px/1.2 Inter,system-ui,sans-serif;letter-spacing:.12em;color:var(--muted);text-transform:uppercase}}
    h1{{margin:8px 0 10px;font-size:clamp(30px,5vw,46px);line-height:1.05}}
    .sub{{color:var(--muted);font-family:Inter,system-ui,sans-serif;font-size:14px}}
    .intro{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-bottom:16px;font-size:18px}}
    .ad-slot{{background:rgba(255,255,255,.03);border:1px dashed #3b5a96;border-radius:12px;padding:12px 14px;margin:0 0 14px 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
    .ad-label{{font:700 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.08em;color:#9cc4ff}}
    .ad-copy{{color:#d9e6ff;font:500 14px/1.3 Inter,system-ui,sans-serif}}
    .ad-cta{{display:inline-block;padding:7px 10px;border-radius:8px;border:1px solid #4c6db0;color:#dff2ff;text-decoration:none;font:600 12px Inter,system-ui,sans-serif}}
    .pick-card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:0 0 14px 0;box-shadow:0 12px 28px rgba(0,0,0,.24)}}
    .pick-head h2{{margin:4px 0 8px;font-size:30px;line-height:1.15}}
    .pick-head{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
    .pick-num{{font:600 12px/1 Inter,system-ui,sans-serif;color:var(--accent);letter-spacing:.12em;text-transform:uppercase}}
    .meta-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px 12px;padding:10px 0 2px}}
    .meta-grid div{{border:1px dashed #31508e;border-radius:10px;padding:8px 10px;background:rgba(255,255,255,.02)}}
    .meta-grid span{{display:block;color:var(--muted);font:600 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px}}
    .meta-grid strong{{font:600 15px/1.35 Inter,system-ui,sans-serif;color:#dce8ff}}
    .lede{{font-size:20px;margin:12px 0 8px;color:#f2f6ff}}
    details{{margin-top:8px;border-top:1px solid #264377;padding-top:8px}}
    summary{{cursor:pointer;font:600 14px Inter,system-ui,sans-serif;color:#fbbf24}}
    ul{{margin:10px 0 0 18px;padding:0}}
    li{{margin:6px 0}}
    .toplinks{{display:flex;gap:10px;margin-top:10px;flex-wrap:wrap}}
    .toplinks a{{display:inline-block;padding:8px 12px;border:1px solid #31508e;border-radius:9px;color:#dce8ff;text-decoration:none;font-family:Inter,system-ui,sans-serif;font-size:13px}}
    footer{{margin-top:10px;color:var(--muted);font:12px Inter,system-ui,sans-serif;text-align:right}}
  </style>
</head>
<body>
  <main class="wrap">
    <header>
      <div class="kicker">SportzBallz Totals Desk</div>
      <h1>Run Total Picks — {html.escape(date_str)}</h1>
      <div class="sub">Model: {html.escape(model)} • Updated {html.escape(now)}</div>
      <div class="toplinks">
        <a href="/{html.escape(date_str)}.html">Full Daily Picks</a>
        <a href="/{html.escape(date_str)}-plus-money.html">Plus Money Picks</a>
        <a href="/">Home</a>
      </div>
    </header>
    <section class="intro">Totals-only leans built from confidence, pricing, weather/venue context, and market movement.</section>
    {_render_ad_slot('run-totals-top', 'Run Totals Sponsorship')}
    {''.join(cards)}
    <footer>Published by SportzBallz.io</footer>
  </main>
</body>
</html>
'''


def _render_top_index(latest_date: str, archive_dates):
    latest_href = f"/{latest_date}.html"
    latest_plus_href = f"/{latest_date}-plus-money.html"
    latest_totals_href = f"/{latest_date}-run-totals.html"

    archive_items = []
    for i, d in enumerate(sorted(set(archive_dates), reverse=True)):
        pill = '<span class="pill">Latest</span>' if i == 0 else ''
        archive_items.append(
            f'<li><a href="/{d}.html"><span>{d} • Daily Picks</span>{pill}</a></li>'
        )
        archive_items.append(
            f'<li><a href="/{d}-plus-money.html"><span>{d} • Plus Money Picks</span></a></li>'
        )
        archive_items.append(
            f'<li><a href="/{d}-run-totals.html"><span>{d} • Run Total Picks</span></a></li>'
        )

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SportzBallz | Daily MLB Picks</title>
  <meta name="description" content="SportzBallz daily MLB picks, commentary, and betting context." />
  <meta name="robots" content="index,follow,max-image-preview:large" />
  <link rel="canonical" href="{_site_url('/')}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="SportzBallz" />
  <meta property="og:title" content="SportzBallz | Daily MLB Picks" />
  <meta property="og:description" content="Daily MLB picks plus underdog and run-total cards, with performance dashboard tracking." />
  <meta property="og:url" content="{_site_url('/')}" />
  <meta name="twitter:card" content="summary_large_image" />
  <style>
    :root {{ --bg:#0a1020; --panel:#111a33; --line:#2a3e72; --ink:#ebf1ff; --muted:#9fb2de; --accent:#63d2ff; --accent2:#7cffc7; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; color:var(--ink); background:radial-gradient(1100px 700px at 10% -5%, #1e2f66 0%, transparent 60%), radial-gradient(900px 600px at 95% 0%, #1b355f 0%, transparent 55%), var(--bg); font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif; min-height:100vh; }}
    .wrap {{ max-width:1100px; margin:0 auto; padding:26px 16px 52px; }}
    .hero {{ border:1px solid var(--line); border-radius:18px; padding:28px 24px; background:linear-gradient(135deg, rgba(99,210,255,.14), rgba(124,255,199,.08)); box-shadow:0 22px 45px rgba(0,0,0,.30); }}
    .kicker {{ color:var(--muted); text-transform:uppercase; letter-spacing:.12em; font-size:12px; margin-bottom:10px; font-weight:700; }}
    .logo {{ margin:0; line-height:1; font-size:clamp(52px, 11vw, 120px); font-weight:900; letter-spacing:.01em; text-transform:uppercase; font-family:Impact,Haettenschweiler,'Arial Narrow Bold',sans-serif; color:#f8fbff; text-shadow:0 2px 0 #0d162e, 2px 2px 0 #0d162e, 3px 3px 0 #0d162e, 4px 4px 0 #0d162e, 0 0 20px rgba(99,210,255,.25); }}
    .logo .z {{ color:#ff5c5c; text-shadow:0 2px 0 #2a0b0b, 2px 2px 0 #2a0b0b, 3px 3px 0 #2a0b0b, 0 0 14px rgba(239,68,68,.35); }}
    .tagline {{ margin:12px 0 0; color:#d9e5ff; font-size:clamp(17px,2.2vw,24px); max-width:760px; line-height:1.35; }}
    .cards {{ margin-top:18px; display:grid; grid-template-columns:1.2fr .8fr; gap:14px; }}
    .card {{ border:1px solid var(--line); border-radius:14px; background:var(--panel); padding:16px; }}
    .card h2 {{ margin:0 0 10px; font-size:21px; line-height:1.2; }}
    .ad-slot{{background:rgba(255,255,255,.03);border:1px dashed #3b5a96;border-radius:12px;padding:12px 14px;margin:14px 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
    .ad-label{{font:700 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.08em;color:#9cc4ff}}
    .ad-copy{{color:#d9e6ff;font:500 14px/1.3 Inter,system-ui,sans-serif}}
    .ad-cta{{display:inline-block;padding:7px 10px;border-radius:8px;border:1px solid #4c6db0;color:#dff2ff;text-decoration:none;font:600 12px Inter,system-ui,sans-serif}}
    .btn {{ display:inline-block; padding:10px 14px; border-radius:10px; text-decoration:none; color:#081224; background:linear-gradient(90deg,var(--accent),var(--accent2)); font-weight:700; margin-top:8px; }}
    .meta {{ font-size:14px; color:var(--muted); margin-top:10px; }}
    ul.archive {{ list-style:none; margin:0; padding:0; display:grid; gap:10px; }}
    ul.archive li a {{ display:flex; justify-content:space-between; align-items:center; gap:10px; text-decoration:none; color:var(--ink); background:rgba(255,255,255,.02); border:1px solid #304b87; border-radius:10px; padding:10px 12px; font-size:15px; }}
    ul.archive li a:hover {{ border-color:var(--accent); transform:translateY(-1px); }}
    .pill {{ font-size:11px; letter-spacing:.09em; text-transform:uppercase; color:#dff4ff; background:rgba(99,210,255,.18); border:1px solid rgba(99,210,255,.35); border-radius:999px; padding:4px 8px; white-space:nowrap; }}
    footer {{ margin-top:16px; color:var(--muted); font-size:12px; text-align:right; }}
    @media (max-width:860px) {{ .cards {{ grid-template-columns:1fr; }} .logo {{ font-size:clamp(44px,18vw,90px); }} }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <div class="kicker">SportzBallz Daily MLB Desk</div>
      <h1 class="logo">SPORT<span class="z">Z</span>BALL<span class="z">Z</span></h1>
      <p class="tagline">artificially intelligent athletic competition prognostication</p>
    </section>

    <section class="cards">
      <article class="card">
        <h2>Latest Daily Picks</h2>
        <p>Today’s full notebook with odds, confidence, pitching, venue/weather, umpire crew, injuries, and market movement.</p>
        <a class="btn" href="{latest_href}">Open {latest_date} Picks</a>
        <a class="btn" href="{latest_plus_href}" style="margin-left:8px; background:linear-gradient(90deg,#22c55e,#7cffc7);">Open {latest_date} Plus Money</a>
        <a class="btn" href="{latest_totals_href}" style="margin-left:8px; background:linear-gradient(90deg,#f59e0b,#fcd34d);">Open {latest_date} Run Totals</a>
        <a class="btn" href="/dashboard.html" style="margin-left:8px; background:linear-gradient(90deg,#8b5cf6,#5cc9ff);">Open Dashboard</a>
        <a class="btn" href="/media-kit.html" style="margin-left:8px; background:linear-gradient(90deg,#4f46e5,#7c3aed);">Media Kit</a>
        <a class="btn" href="/rate-card.html" style="margin-left:8px; background:linear-gradient(90deg,#0ea5e9,#22d3ee);">Rate Card</a>
        <div class="meta">Format: <code>yyyy-mm-dd.html</code></div>
        {_render_ad_slot('index-hero', 'Homepage Sponsorship')}
      </article>

      <article class="card">
        <h2>Archive</h2>
        <ul class="archive">
          {''.join(archive_items)}
        </ul>
      </article>
    </section>

    <footer>© SportzBallz.io</footer>
  </main>
</body>
</html>
'''


def _find_archive_dates(site_repo: Path):
    dates = []
    pattern = re.compile(r'^(\d{4}-\d{2}-\d{2})\.html$')
    for p in site_repo.glob('*.html'):
        m = pattern.match(p.name)
        if m:
            dates.append(m.group(1))
    return sorted(set(dates), reverse=True)


def _load_history(site_repo: Path):
    data_dir = site_repo / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    history_path = data_dir / 'performance-history.json'
    if not history_path.exists():
        return history_path, []
    try:
        data = json.loads(history_path.read_text())
        if isinstance(data, list):
            return history_path, data
    except Exception:
        pass
    return history_path, []


def _upsert_history(history, summary):
    out = [h for h in history if h.get('date') != summary.get('date')]
    out.append(summary)
    out.sort(key=lambda x: x.get('date', ''), reverse=True)
    return out


def _render_dashboard(history):
    if history:
        total_picks = sum(h.get('total_picks', 0) for h in history)
        total_decided = sum(h.get('decided', 0) for h in history)
        total_wins = sum(h.get('wins', 0) for h in history)
        total_losses = sum(h.get('losses', 0) for h in history)
        overall_wr = round((total_wins / total_decided) * 100, 1) if total_decided else None
        total_pm_decided = sum(h.get('plus_money_decided', 0) for h in history)
        total_pm_wins = sum(h.get('plus_money_wins', 0) for h in history)
        total_pm_losses = sum(h.get('plus_money_losses', 0) for h in history)
        overall_pm_wr = round((total_pm_wins / total_pm_decided) * 100, 1) if total_pm_decided else None
    else:
        total_picks = total_decided = total_wins = total_losses = 0
        total_pm_decided = total_pm_wins = total_pm_losses = 0
        overall_wr = overall_pm_wr = None

    rows = []
    for h in history:
        wr = f"{h.get('win_rate')}%" if h.get('win_rate') is not None else '—'
        pwr = f"{h.get('plus_money_win_rate')}%" if h.get('plus_money_win_rate') is not None else '—'
        d = h.get('date', '')
        rows.append(
            f"<tr><td><a href='/{d}.html'>{d}</a></td><td>{h.get('wins',0)}-{h.get('losses',0)}</td><td>{wr}</td><td>{h.get('plus_money_wins',0)}-{h.get('plus_money_losses',0)}</td><td>{pwr}</td><td>{h.get('pending',0)}</td></tr>"
        )

    overall_wr_txt = f"{overall_wr}%" if overall_wr is not None else '—'
    overall_pm_txt = f"{overall_pm_wr}%" if overall_pm_wr is not None else '—'

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SportzBallz | Performance Dashboard</title>
  <meta name="description" content="SportzBallz historical MLB pick performance, records, and plus-money metrics." />
  <meta name="robots" content="index,follow,max-image-preview:large" />
  <link rel="canonical" href="{_site_url('/dashboard.html')}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="SportzBallz" />
  <meta property="og:title" content="SportzBallz | Performance Dashboard" />
  <meta property="og:description" content="Track win rates, records, and plus-money outcomes over time." />
  <meta property="og:url" content="{_site_url('/dashboard.html')}" />
  <meta name="twitter:card" content="summary_large_image" />
  <style>
    :root {{ --bg:#0a1020; --panel:#101a33; --ink:#eaf0ff; --muted:#a7b7df; --line:#273a6b; --accent:#5cc9ff; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:radial-gradient(1200px 700px at 15% -10%, #1a2a55, var(--bg)); color:var(--ink); font-family:Inter,system-ui,sans-serif; }}
    .wrap {{ max-width:1100px; margin:0 auto; padding:24px 16px 48px; }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:14px; margin-bottom:14px; }}
    h1 {{ margin:0 0 8px; font-size:34px; }}
    .meta {{ color:var(--muted); margin-bottom:8px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:10px; }}
    .ad-slot{{background:rgba(255,255,255,.03);border:1px dashed #3b5a96;border-radius:12px;padding:12px 14px;margin:12px 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
    .ad-label{{font:700 11px/1 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.08em;color:#9cc4ff}}
    .ad-copy{{color:#d9e6ff;font:500 14px/1.3 Inter,system-ui,sans-serif}}
    .ad-cta{{display:inline-block;padding:7px 10px;border-radius:8px;border:1px solid #4c6db0;color:#dff2ff;text-decoration:none;font:600 12px Inter,system-ui,sans-serif}}
    .k {{ border:1px dashed #31508e; border-radius:10px; padding:10px; }}
    .k span {{ display:block; color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.08em; margin-bottom:4px; }}
    .k strong {{ font-size:20px; }}
    table {{ width:100%; border-collapse:collapse; }}
    th, td {{ border-bottom:1px solid #2a3f70; padding:10px 8px; text-align:left; }}
    th {{ color:#cfe0ff; font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
    td {{ color:#e2ecff; }}
    a {{ color:#8ad8ff; text-decoration:none; }}
    .links a {{ display:inline-block; margin-right:8px; border:1px solid #31508e; border-radius:8px; padding:6px 10px; }}
  </style>
</head>
<body>
  <main class="wrap">
    <div class="card">
      <h1>Performance Dashboard</h1>
      <div class="meta">Auto-tracked from published daily picks.</div>
      <div class="links"><a href="/">Home</a> <a href="/media-kit.html">Media Kit</a> <a href="/rate-card.html">Rate Card</a></div>
      {_render_ad_slot('dashboard-top', 'Dashboard Sponsorship')}
      <div class="grid">
        <div class="k"><span>Total Picks</span><strong>{total_picks}</strong></div>
        <div class="k"><span>Decided</span><strong>{total_decided}</strong></div>
        <div class="k"><span>Overall Record</span><strong>{total_wins}-{total_losses}</strong></div>
        <div class="k"><span>Overall Win %</span><strong>{overall_wr_txt}</strong></div>
        <div class="k"><span>Plus Money Record</span><strong>{total_pm_wins}-{total_pm_losses}</strong></div>
        <div class="k"><span>Plus Money Win %</span><strong>{overall_pm_txt}</strong></div>
      </div>
    </div>

    <div class="card">
      <h2 style="margin-top:0">Daily Performance</h2>
      <table>
        <thead><tr><th>Date</th><th>Record</th><th>Win %</th><th>Plus Money</th><th>Plus %</th><th>Pending</th></tr></thead>
        <tbody>
          {''.join(rows) if rows else '<tr><td colspan="6">No history yet.</td></tr>'}
        </tbody>
      </table>
    </div>
  </main>
</body>
</html>
'''


def _run(cmd, cwd):
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)


def publish_daily_site(markdown_path: str, site_repo_path: str = None):
    md_file = Path(markdown_path)
    if not md_file.exists():
        return None

    parsed = _parse_markdown(md_file.read_text())
    if not parsed['date']:
        # derive from filename fallback: YYYY-MM-DD-pick.md
        m = re.search(r'(\d{4}-\d{2}-\d{2})', md_file.name)
        if not m:
            return None
        parsed['date'] = m.group(1)

    if site_repo_path:
        site_repo = Path(site_repo_path)
    else:
        site_repo = Path(__file__).resolve().parents[3] / 'sportzballz.io'

    if not site_repo.exists():
        print(f"Site repo not found: {site_repo}")
        return None

    evaluated_picks, summary = _evaluate_picks(parsed)

    date_html = site_repo / f"{parsed['date']}.html"
    date_html.write_text(_render_daily_html(parsed, evaluated_picks, summary))

    plus_html = site_repo / f"{parsed['date']}-plus-money.html"
    plus_html.write_text(_render_plus_money_html(parsed, evaluated_picks, summary))

    totals_html = site_repo / f"{parsed['date']}-run-totals.html"
    totals_html.write_text(_render_run_totals_html(parsed, evaluated_picks))

    history_path, history = _load_history(site_repo)
    history = _upsert_history(history, summary)
    history_path.write_text(json.dumps(history, indent=2))
    (site_repo / 'dashboard.html').write_text(_render_dashboard(history))
    (site_repo / 'media-kit.html').write_text(_render_media_kit())
    (site_repo / 'rate-card.html').write_text(_render_rate_card())

    archive = _find_archive_dates(site_repo)
    if parsed['date'] not in archive:
        archive = [parsed['date']] + archive
    (site_repo / 'index.html').write_text(_render_top_index(parsed['date'], archive))
    (site_repo / 'robots.txt').write_text(_render_robots_txt())
    (site_repo / 'sitemap.xml').write_text(_render_sitemap_xml(archive))

    auto_publish = os.environ.get('AUTO_PUBLISH_SITE', 'true').lower() in ('1', 'true', 'yes', 'on')
    if not auto_publish:
        return str(date_html)

    # Commit + push any changes
    add = _run([
        'git', 'add', 'index.html', 'dashboard.html', 'data/performance-history.json',
        'media-kit.html', 'rate-card.html', 'robots.txt', 'sitemap.xml',
        f"{parsed['date']}.html", f"{parsed['date']}-plus-money.html", f"{parsed['date']}-run-totals.html"
    ], site_repo)
    if add.returncode != 0:
        print(add.stderr.strip())
        return str(date_html)

    status = _run(['git', 'status', '--porcelain'], site_repo)
    if status.returncode != 0 or not status.stdout.strip():
        return str(date_html)

    commit_msg = f"Auto-publish daily picks {parsed['date']}"
    commit = _run(['git', 'commit', '-m', commit_msg], site_repo)
    if commit.returncode != 0:
        print(commit.stderr.strip() or commit.stdout.strip())
        return str(date_html)

    push = _run(['git', 'push', 'origin', 'main'], site_repo)
    if push.returncode != 0:
        print(push.stderr.strip() or push.stdout.strip())
    else:
        print(f"Auto-published site for {parsed['date']}")

    return str(date_html)
