import json
import os
from datetime import datetime, timedelta

import pytz
import requests
import statsapi

from common.util import get_teams_list
from connector.mlbstartinglineups import get_starting_lineups

RECENT_LINEUP_GAMES = 5

DOME_VENUES = {
    "Rogers Centre",
    "Tropicana Field",
    "loanDepot park",
    "Minute Maid Park",
    "American Family Field",
    "Chase Field",
    "T-Mobile Park",
    "Globe Life Field",
}


def _safe_get(dct, path, default=None):
    cur = dct
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


def _normalize_abbr(abbr):
    # predictions can include markers like $, ., *
    return abbr.replace("$", "").replace(".", "").replace("*", "").strip().lower()


def _get_team_maps():
    teams = get_teams_list()
    abbr_to_name = {}
    name_to_id = {}
    for t in teams:
        abbr_to_name[t.abbreviation.strip().lower()] = t.name
        name_to_id[t.name] = t.id
    return abbr_to_name, name_to_id


def _build_schedule_lookup(game_date):
    games = statsapi.schedule(start_date=game_date, end_date=game_date)
    return games


def _find_game_for_pick(schedule, winner_name, loser_name):
    for g in schedule:
        home = g.get("home_name")
        away = g.get("away_name")
        if {winner_name, loser_name} == {home, away}:
            return g
    return None


def _extract_umpires(game_data):
    officials = _safe_get(game_data, ["liveData", "boxscore", "officials"], []) or []
    crew = []
    for o in officials:
        name = _safe_get(o, ["official", "fullName"], "Unknown")
        role = o.get("officialType", "Official")
        crew.append(f"{role}: {name}")
    return crew


def _extract_weather(game_data):
    weather = _safe_get(game_data, ["gameData", "weather"], {}) or {}
    venue = _safe_get(game_data, ["gameData", "venue", "name"], "Unknown Venue")
    dome = venue in DOME_VENUES

    if dome:
        return {
            "venue": venue,
            "dome": True,
            "summary": "Dome/retractable roof environment — external wind conditions not applicable.",
            "temp": None,
            "wind": None,
            "condition": None,
        }

    condition = weather.get("condition")
    temp = weather.get("temp")
    wind = weather.get("wind")

    if condition or temp or wind:
        summary_parts = []
        if condition:
            summary_parts.append(str(condition))
        if temp:
            summary_parts.append(f"{temp}°F")
        if wind:
            summary_parts.append(str(wind))
        summary = ", ".join(summary_parts)
    else:
        summary = "Weather data unavailable from MLB feed at run time."

    return {
        "venue": venue,
        "dome": False,
        "summary": summary,
        "temp": temp,
        "wind": wind,
        "condition": condition,
    }


def _get_injuries(team_id):
    try:
        url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?rosterType=injured"
        resp = requests.get(url, timeout=8)
        if resp.status_code != 200:
            return []
        data = resp.json()
        roster = data.get("roster", [])
        injuries = []
        for r in roster:
            name = _safe_get(r, ["person", "fullName"], "Unknown")
            status = _safe_get(r, ["status", "description"], "Injured list")
            injuries.append(f"{name} ({status})")
        return injuries[:8]
    except Exception:
        return []


def _extract_line_movement(odds_entry, winner_name):
    if not odds_entry:
        return {"current": None, "open": None, "movement": None, "text": "Line movement unavailable."}

    teams = odds_entry.get("teams", {})
    side = "home" if _safe_get(teams, ["home", "team"]) == winner_name else "away"

    odds_obj = None
    if odds_entry.get("odds") and len(odds_entry["odds"]) > 0:
        odds_obj = odds_entry["odds"][0]

    current = _safe_get(odds_obj or {}, ["moneyline", "current", f"{side}Odds"])

    # Try multiple possible open keys from provider payloads
    open_odds = (
        _safe_get(odds_obj or {}, ["moneyline", "opening", f"{side}Odds"])
        or _safe_get(odds_obj or {}, ["moneyline", "open", f"{side}Odds"])
        or _safe_get(odds_obj or {}, ["moneyline", "opening", side])
        or _safe_get(odds_obj or {}, ["moneyline", "open", side])
    )

    movement = None
    if isinstance(current, (int, float)) and isinstance(open_odds, (int, float)):
        movement = current - open_odds

    if current is None:
        text = "Current moneyline unavailable."
    elif open_odds is None:
        text = f"Current moneyline: {current}. Opening line not available from feed."
    elif movement == 0:
        text = f"Moneyline unchanged at {current}."
    else:
        direction = "toward" if movement < 0 else "away from"
        text = f"Moneyline moved from {open_odds} to {current} ({movement:+}), {direction} the pick side."

    return {"current": current, "open": open_odds, "movement": movement, "text": text}


def _extract_total_market(odds_entry):
    if not odds_entry:
        return {
            "total_current": None,
            "over_odds": None,
            "under_odds": None,
            "total_open": None,
            "text": "Total line unavailable.",
            "movement_text": "Total movement unavailable.",
        }

    odds_obj = None
    if odds_entry.get("odds") and len(odds_entry["odds"]) > 0:
        odds_obj = odds_entry["odds"][0]

    total_current = _safe_get(odds_obj or {}, ["total", "current", "total"])
    over_odds = _safe_get(odds_obj or {}, ["total", "current", "overOdds"])
    under_odds = _safe_get(odds_obj or {}, ["total", "current", "underOdds"])
    total_open = _safe_get(odds_obj or {}, ["total", "open", "total"])

    if total_current is None:
        text = "Total line unavailable."
    else:
        text = f"{total_current} (Over {over_odds if over_odds is not None else '—'} / Under {under_odds if under_odds is not None else '—'})"

    if total_current is None or total_open is None:
        movement_text = "Total movement unavailable."
    else:
        diff = float(total_current) - float(total_open)
        if diff == 0:
            movement_text = f"Total unchanged at {total_current}."
        elif diff > 0:
            movement_text = f"Total moved up from {total_open} to {total_current} (+{diff:g})."
        else:
            movement_text = f"Total moved down from {total_open} to {total_current} ({diff:g})."

    return {
        "total_current": total_current,
        "over_odds": over_odds,
        "under_odds": under_odds,
        "total_open": total_open,
        "text": text,
        "movement_text": movement_text,
    }


def _format_odds(odds):
    try:
        o = int(odds)
        if o > 0:
            return f"+{o}"
        if o < 0:
            return str(o)
    except Exception:
        pass
    return "----"


def _lineup_announced(team_token):
    token = str(team_token or "").strip()
    # Historical marker convention from prediction payload:
    # leading "." means lineup not yet posted for that team.
    # A leading "$" can also be present for in-game winner marker.
    token = token.lstrip("$")
    return not token.startswith('.')


def _lineup_status_text(winner_name, loser_name, winner_announced, loser_announced):
    if winner_announced and loser_announced:
        return "Both starting lineups were announced at publish time."
    if (not winner_announced) and (not loser_announced):
        return "Starting lineups were not announced for either team at publish time."
    if winner_announced and (not loser_announced):
        return f"{winner_name} lineup announced; {loser_name} lineup not announced at publish time."
    return f"{winner_name} lineup not announced; {loser_name} lineup announced at publish time."


def _today_lineups_by_team():
    out = {}
    try:
        for lu in get_starting_lineups() or []:
            ids = []
            for p in getattr(lu, "lineup_players", []) or []:
                try:
                    ids.append(int(p.get("personId")))
                except Exception:
                    continue
            if ids:
                out[int(lu.team_id)] = ids[:9]
    except Exception:
        return {}
    return out


def _recent_team_games(team_id, as_of_date, max_games=RECENT_LINEUP_GAMES):
    # Pull enough history window to capture previous few completed games.
    end_date = datetime.strptime(as_of_date, "%Y-%m-%d").date() - timedelta(days=1)
    start_date = end_date - timedelta(days=25)
    try:
        games = statsapi.schedule(
            start_date=str(start_date),
            end_date=str(end_date),
            team=team_id,
        )
    except Exception:
        games = []

    games = sorted(games, key=lambda g: g.get("game_datetime") or "", reverse=True)
    return games[:max_games]


def _team_lineup_and_result_for_game(game_pk, team_id):
    try:
        game = statsapi.get("game", {"gamePk": game_pk})
    except Exception:
        return [], None

    home_id = _safe_get(game, ["gameData", "teams", "home", "id"])
    away_id = _safe_get(game, ["gameData", "teams", "away", "id"])
    side = "home" if home_id == team_id else ("away" if away_id == team_id else None)
    if not side:
        return [], None

    order = _safe_get(game, ["liveData", "boxscore", "teams", side, "battingOrder"], []) or []
    lineup_ids = []
    for pid in order[:9]:
        try:
            lineup_ids.append(int(pid))
        except Exception:
            continue

    team_runs = _safe_get(game, ["liveData", "linescore", "teams", side, "runs"])
    opp_side = "away" if side == "home" else "home"
    opp_runs = _safe_get(game, ["liveData", "linescore", "teams", opp_side, "runs"])
    won = None
    if isinstance(team_runs, int) and isinstance(opp_runs, int):
        won = team_runs > opp_runs

    return lineup_ids, won


def _lineup_change_impact(team_id, team_name, today_lineup_ids, as_of_date):
    if not today_lineup_ids:
        return ""

    recent = _recent_team_games(team_id, as_of_date, RECENT_LINEUP_GAMES)
    if not recent:
        return ""

    today_set = set(today_lineup_ids)
    overlaps = []
    turnover_wins = turnover_total = 0
    stable_wins = stable_total = 0

    for g in recent:
        game_pk = g.get("game_id")
        if not game_pk:
            continue
        prev_ids, won = _team_lineup_and_result_for_game(game_pk, team_id)
        if not prev_ids:
            continue
        shared = len(today_set.intersection(set(prev_ids)))
        overlaps.append(shared)

        if won is None:
            continue
        if shared <= 6:
            turnover_total += 1
            if won:
                turnover_wins += 1
        elif shared >= 8:
            stable_total += 1
            if won:
                stable_wins += 1

    if not overlaps:
        return ""

    avg_shared = round(sum(overlaps) / len(overlaps), 1)
    base = f"Compared with last {len(overlaps)} games, today's announced lineup shares {avg_shared}/9 starters on average."

    impact_bits = []
    if turnover_total >= 2:
        impact_bits.append(f"In higher-turnover comps (≤6 shared), {team_name} went {turnover_wins}-{turnover_total - turnover_wins}")
    if stable_total >= 2:
        impact_bits.append(f"in stable-lineup comps (≥8 shared), {team_name} went {stable_wins}-{stable_total - stable_wins}")

    if impact_bits:
        return base + " " + "; ".join(impact_bits) + "."
    return base


def _fallback_commentary(context):
    venue = context["venue"]
    weather = context["weather_summary"]
    movement = context["line_movement_text"]
    ump = context["umpire_summary"]
    lineup_status = context.get("lineup_status_text", "Starting lineup status unavailable at publish time.")
    lineup_impact = context.get("lineup_change_impact", "")
    lineup_impact_sentence = f" {lineup_impact}" if lineup_impact else ""
    style = context.get("style", "betting desk")
    winner_signals = context.get("winner_signals", "No model signal list available.")
    loser_signals = context.get("loser_signals", "No model signal list available.")

    if style == "beat writer notebook":
        return (
            f"{venue} sets the stage for {context['winner']} over {context['loser']}, and the conditions matter: {weather}. "
            f"The model sits at {context['confidence']} confidence with {context['data_points']} data-point leverage, which gives the pick real footing. "
            f"On the baseball side, the edge profile for {context['winner']} is driven by {winner_signals}. "
            f"The counter-case for {context['loser']} shows up in {loser_signals}, but the market signal ({movement}) still leans playable. "
            f"Umpire context ({ump}) is a late-variable worth watching, but this spot grades as a disciplined position rather than a flyer. "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )
    if style == "scouting report":
        return (
            f"Scouting read: {context['winning_pitcher']} vs {context['losing_pitcher']} favors {context['winner']} at {context['odds']}. "
            f"Model confidence ({context['confidence']}, data points {context['data_points']}) supports the same direction. "
            f"Signal stack for {context['winner']}: {winner_signals}. "
            f"Opposition signal stack for {context['loser']}: {loser_signals}. "
            f"Add weather ({weather}), umpire texture ({ump}), and line behavior ({movement}) and this profile stays actionable. "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )
    if style == "game-script breakdown":
        return (
            f"Game-script angle: {context['winner']} projects cleaner paths to control innings than {context['loser']}, starting with {context['winning_pitcher']} over {context['losing_pitcher']}. "
            f"The model calls it {context['confidence']} with {context['data_points']} data points and a listed number of {context['odds']}. "
            f"Early/ongoing pressure indicators for {context['winner']} show up in {winner_signals}. "
            f"Pushback factors for {context['loser']} are {loser_signals}. "
            f"Environment ({weather}), crew ({ump}), and market movement ({movement}) all point to the same side unless live conditions materially shift. "
            f"Lineup status: {lineup_status}{lineup_impact_sentence}"
        )

    return (
        f"Price-first view: {context['winner']} over {context['loser']} at {context['odds']} with model confidence {context['confidence']} ({context['data_points']}). "
        f"The strongest support for {context['winner']} comes from: {winner_signals}. "
        f"The best resistance case for {context['loser']} comes from: {loser_signals}. "
        f"Venue/weather ({venue}, {weather}), umpire notes ({ump}), and market movement ({movement}) keep this in the value bucket. "
        f"Lineup status: {lineup_status}{lineup_impact_sentence}"
    )


def _generate_commentary(context):
    # Deterministic in-process commentary only.
    # No external LLM calls.
    return _fallback_commentary(context)


def write_daily_pick_markdown(predictions, odds_data, model_name):
    valid = [p for p in predictions if p.winning_team != '-']
    if not valid:
        return None

    eastern = pytz.timezone("US/Eastern")
    today = str(datetime.now(eastern).date())

    abbr_to_name, name_to_id = _get_team_maps()
    schedule = _build_schedule_lookup(today)
    todays_lineups = _today_lineups_by_team()

    odds_lookup = {}
    for o in odds_data.get("results", []):
        home = _safe_get(o, ["teams", "home", "team"])
        away = _safe_get(o, ["teams", "away", "team"])
        if home and away:
            odds_lookup[frozenset([home, away])] = o

    lines = []
    lines.append(f"# MLB Picks Commentary — {today}")
    lines.append("")
    lines.append(f"- Model: `{model_name}`")
    lines.append(f"- Generated: {datetime.now(eastern).strftime('%Y-%m-%d %I:%M %p %Z')}")
    lines.append("")

    for idx, p in enumerate(valid, start=1):
        winner_lineup_announced = _lineup_announced(p.winning_team)
        loser_lineup_announced = _lineup_announced(p.losing_team)

        winner_abbr = _normalize_abbr(p.winning_team)
        loser_abbr = _normalize_abbr(p.losing_team)

        winner_name = abbr_to_name.get(winner_abbr, winner_abbr.upper())
        loser_name = abbr_to_name.get(loser_abbr, loser_abbr.upper())

        game = _find_game_for_pick(schedule, winner_name, loser_name)
        game_data = statsapi.get("game", {"gamePk": game["game_id"]}) if game else {}

        weather = _extract_weather(game_data) if game_data else {
            "venue": "Unknown Venue",
            "summary": "Weather unavailable.",
            "dome": False,
        }

        umpires = _extract_umpires(game_data) if game_data else []
        ump_summary = "; ".join(umpires) if umpires else "Umpire crew unavailable at run time."

        winner_id = name_to_id.get(winner_name)
        loser_id = name_to_id.get(loser_name)
        winner_injuries = _get_injuries(winner_id) if winner_id else []
        loser_injuries = _get_injuries(loser_id) if loser_id else []

        winner_lineup_impact = _lineup_change_impact(
            winner_id,
            winner_name,
            todays_lineups.get(winner_id, []),
            today,
        ) if winner_id else ""
        loser_lineup_impact = _lineup_change_impact(
            loser_id,
            loser_name,
            todays_lineups.get(loser_id, []),
            today,
        ) if loser_id else ""

        impact_parts = []
        if winner_lineup_impact:
            impact_parts.append(f"{winner_name}: {winner_lineup_impact}")
        if loser_lineup_impact:
            impact_parts.append(f"{loser_name}: {loser_lineup_impact}")
        lineup_change_impact = " ".join(impact_parts)

        odds_entry = odds_lookup.get(frozenset([winner_name, loser_name]))
        line_move = _extract_line_movement(odds_entry, winner_name)
        total_market = _extract_total_market(odds_entry)

        context = {
            "pick_index": idx,
            "style": ["betting desk", "beat writer notebook", "scouting report", "game-script breakdown"][(idx - 1) % 4],
            "winner": winner_name,
            "loser": loser_name,
            "odds": _format_odds(p.odds),
            "confidence": p.confidence,
            "data_points": p.data_points,
            "winner_signals": ", ".join(p.winning_stats[:15]) if p.winning_stats else "No model signal list available.",
            "loser_signals": ", ".join(p.losing_stats[:15]) if p.losing_stats else "No model signal list available.",
            "venue": weather.get("venue", "Unknown Venue"),
            "weather_summary": weather.get("summary", "Weather unavailable."),
            "umpire_summary": ump_summary,
            "winner_injuries": ", ".join(winner_injuries) if winner_injuries else "No injured-list data available.",
            "loser_injuries": ", ".join(loser_injuries) if loser_injuries else "No injured-list data available.",
            "line_movement_text": line_move["text"],
            "total_line_text": total_market["text"],
            "total_movement_text": total_market["movement_text"],
            "winner_lineup_announced": winner_lineup_announced,
            "loser_lineup_announced": loser_lineup_announced,
            "lineup_status_text": _lineup_status_text(winner_name, loser_name, winner_lineup_announced, loser_lineup_announced),
            "winner_lineup_trend": winner_lineup_impact,
            "loser_lineup_trend": loser_lineup_impact,
            "lineup_change_impact": lineup_change_impact,
            "winning_pitcher": p.winning_pitcher,
            "losing_pitcher": p.losing_pitcher,
        }

        commentary = _generate_commentary(context)

        lines.append(f"## {idx}) {winner_name} over {loser_name}")
        lines.append("")
        lines.append(f"- **Pick Odds:** {context['odds']}")
        lines.append(f"- **Model Confidence:** {context['confidence']} (data points: {context['data_points']})")
        lines.append(f"- **Pitching Matchup:** {context['winning_pitcher']} vs {context['losing_pitcher']}")
        lines.append(f"- **{winner_name} Model Signals:** {context['winner_signals']}")
        lines.append(f"- **{loser_name} Model Signals:** {context['loser_signals']}")
        lines.append(f"- **Venue:** {context['venue']}")
        lines.append(f"- **Weather:** {context['weather_summary']}")
        lines.append(f"- **Umpire Crew:** {context['umpire_summary']}")
        lines.append(f"- **{winner_name} Injuries:** {context['winner_injuries']}")
        lines.append(f"- **{loser_name} Injuries:** {context['loser_injuries']}")
        lines.append(f"- **Starting Lineups:** {context['lineup_status_text']}")
        lines.append(f"- **{winner_name} Lineup Trend:** {context['winner_lineup_trend'] or 'n/a'}")
        lines.append(f"- **{loser_name} Lineup Trend:** {context['loser_lineup_trend'] or 'n/a'}")
        lines.append(f"- **Lineup Change Impact:** {context['lineup_change_impact'] or 'n/a'}")
        lines.append(f"- **Line Movement:** {context['line_movement_text']}")
        lines.append(f"- **Total Line:** {context['total_line_text']}")
        lines.append(f"- **Total Movement:** {context['total_movement_text']}")
        lines.append("")
        lines.append("**Commentary**")
        lines.append("")
        lines.append(commentary)
        lines.append("")

    output_dir = "./picks"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{today}-pick.md")

    with open(output_path, "w") as f:
        f.write("\n".join(lines).strip() + "\n")

    return output_path
