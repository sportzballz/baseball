import os
import re
import html
import subprocess
from pathlib import Path
from datetime import datetime


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


def _warm_paragraph(pick):
    winner, loser = pick['winner'], pick['loser']
    odds = _field(pick, 'Pick Odds', '----')
    conf = _field(pick, 'Model Confidence', 'n/a').split(' ')[0]
    pitching = _field(pick, 'Pitching Matchup', 'matchup unavailable')
    venue = _field(pick, 'Venue', 'Unknown venue')
    weather = _field(pick, 'Weather', 'Weather unavailable')
    ump = _field(pick, 'Umpire Crew', 'Umpire crew unavailable')
    move = _field(pick, 'Line Movement', 'Line movement unavailable')

    return (
        f"This one leans <strong>{html.escape(winner)} over {html.escape(loser)}</strong> at "
        f"<strong>{html.escape(odds)}</strong>, with model confidence around <strong>{html.escape(conf)}</strong>. "
        f"The pitching lane is {html.escape(pitching)}, and the venue/weather context at {html.escape(venue)} "
        f"({html.escape(weather)}) gives the matchup texture. Umpire assignment ({html.escape(ump)}) and market signal "
        f"({html.escape(move)}) round out the read. The case here is classic baseball handicapping: spot, starter, and price all in conversation."
    )


def _render_daily_html(parsed):
    picks = parsed['picks']
    date_str = parsed['date']
    model = parsed['model']
    now = datetime.now().strftime('%Y-%m-%d %I:%M %p')

    cards = []
    for i, p in enumerate(picks, 1):
        winner, loser = p['winner'], p['loser']
        cards.append(f'''
      <article class="pick-card">
        <div class="pick-head">
          <div class="pick-num">Pick {i}</div>
          <h2>{html.escape(winner)} over {html.escape(loser)}</h2>
        </div>
        <div class="meta-grid">
          <div><span>Odds</span><strong>{html.escape(_field(p,'Pick Odds','----'))}</strong></div>
          <div><span>Confidence</span><strong>{html.escape(_field(p,'Model Confidence','n/a'))}</strong></div>
          <div><span>Pitching</span><strong>{html.escape(_field(p,'Pitching Matchup','n/a'))}</strong></div>
          <div><span>Venue</span><strong>{html.escape(_field(p,'Venue','n/a'))}</strong></div>
        </div>
        <p class="lede">{_warm_paragraph(p)}</p>
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
    .pick-num{{font:600 12px/1 Inter,system-ui,sans-serif;color:var(--accent);letter-spacing:.12em;text-transform:uppercase}}
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
    {''.join(cards)}
    <footer>Published by SportzBallz.io</footer>
  </main>
</body>
</html>
'''


def _render_top_index(latest_date: str, archive_dates):
    latest_href = f"/{latest_date}.html"

    archive_items = []
    for i, d in enumerate(sorted(set(archive_dates), reverse=True)):
        pill = '<span class="pill">Latest</span>' if i == 0 else ''
        archive_items.append(
            f'<li><a href="/{d}.html"><span>{d}</span>{pill}</a></li>'
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

    date_html = site_repo / f"{parsed['date']}.html"
    date_html.write_text(_render_daily_html(parsed))

    archive = _find_archive_dates(site_repo)
    if parsed['date'] not in archive:
        archive = [parsed['date']] + archive
    (site_repo / 'index.html').write_text(_render_top_index(parsed['date'], archive))

    auto_publish = os.environ.get('AUTO_PUBLISH_SITE', 'true').lower() in ('1', 'true', 'yes', 'on')
    if not auto_publish:
        return str(date_html)

    # Commit + push any changes
    add = _run(['git', 'add', 'index.html', f"{parsed['date']}.html"], site_repo)
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
