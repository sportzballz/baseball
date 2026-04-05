import os
import re
import html
import json
import subprocess
from pathlib import Path
from datetime import datetime
import statsapi


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

    voices = [
        (
            "Insider notebook:",
            f"{winner} over {loser} lands as a {bucket} position at {odds}, with confidence {conf_text} and a {dp_text} data-point split. "
            f"The matchup starts on the mound ({pitching}) and extends into signal texture, with {winner} carrying a broader indicator stack "
            f"({w_sig_count} signals) versus {loser} ({l_sig_count})."
        ),
        (
            "Beat-writer lens:",
            f"On today’s board, {winner} over {loser} reads more process than noise. The number ({odds}) and confidence profile ({conf_text}) "
            f"suggest a {bucket} edge, anchored by the pitching lane ({pitching}) and supported by the model’s side-specific indicator balance."
        ),
        (
            "Scouting report:",
            f"This ticket points to {winner} over {loser}, with model confidence {conf_text} ({dp_text} data points) and a market entry around {odds}. "
            f"Primary baseball drivers remain the pitcher pairing ({pitching}) and a stronger quantitative profile on the {winner} side."
        ),
        (
            "Game-script view:",
            f"The projected flow favors {winner} over {loser}: confidence sits at {conf_text}, odds at {odds}, and the opening script starts with {pitching}. "
            f"Indicator composition suggests {winner} has cleaner paths to leverage innings in this spot."
        ),
    ]

    prefix, lead = voices[(idx - 1) % len(voices)]
    return (
        f"{prefix} {lead} "
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
    {pm_summary_html}
    {''.join(cards)}
    <footer>Published by SportzBallz.io</footer>
  </main>
</body>
</html>
'''


def _render_top_index(latest_date: str, archive_dates):
    latest_href = f"/{latest_date}.html"
    latest_plus_href = f"/{latest_date}-plus-money.html"

    archive_items = []
    for i, d in enumerate(sorted(set(archive_dates), reverse=True)):
        pill = '<span class="pill">Latest</span>' if i == 0 else ''
        archive_items.append(
            f'<li><a href="/{d}.html"><span>{d} • Daily Picks</span>{pill}</a></li>'
        )
        archive_items.append(
            f'<li><a href="/{d}-plus-money.html"><span>{d} • Plus Money Picks</span></a></li>'
        )

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SportzBallz | Daily MLB Picks</title>
  <meta name="description" content="SportzBallz daily MLB picks, commentary, and betting context." />
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
        <a class="btn" href="/dashboard.html" style="margin-left:8px; background:linear-gradient(90deg,#8b5cf6,#5cc9ff);">Open Dashboard</a>
        <div class="meta">Format: <code>yyyy-mm-dd.html</code></div>
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
  <style>
    :root {{ --bg:#0a1020; --panel:#101a33; --ink:#eaf0ff; --muted:#a7b7df; --line:#273a6b; --accent:#5cc9ff; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:radial-gradient(1200px 700px at 15% -10%, #1a2a55, var(--bg)); color:var(--ink); font-family:Inter,system-ui,sans-serif; }}
    .wrap {{ max-width:1100px; margin:0 auto; padding:24px 16px 48px; }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:14px; margin-bottom:14px; }}
    h1 {{ margin:0 0 8px; font-size:34px; }}
    .meta {{ color:var(--muted); margin-bottom:8px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:10px; }}
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
      <div class="links"><a href="/">Home</a></div>
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

    history_path, history = _load_history(site_repo)
    history = _upsert_history(history, summary)
    history_path.write_text(json.dumps(history, indent=2))
    (site_repo / 'dashboard.html').write_text(_render_dashboard(history))

    archive = _find_archive_dates(site_repo)
    if parsed['date'] not in archive:
        archive = [parsed['date']] + archive
    (site_repo / 'index.html').write_text(_render_top_index(parsed['date'], archive))

    auto_publish = os.environ.get('AUTO_PUBLISH_SITE', 'true').lower() in ('1', 'true', 'yes', 'on')
    if not auto_publish:
        return str(date_html)

    # Commit + push any changes
    add = _run([
        'git', 'add', 'index.html', 'dashboard.html', 'data/performance-history.json',
        f"{parsed['date']}.html", f"{parsed['date']}-plus-money.html"
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
