import json
import os
from datetime import datetime

import pytz
import requests
import statsapi
from openai import OpenAI

from common.util import get_teams_list

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


def _fallback_commentary(context):
    venue = context["venue"]
    weather = context["weather_summary"]
    movement = context["line_movement_text"]
    ump = context["umpire_summary"]
    style = context.get("style", "betting desk")
    winner_signals = context.get("winner_signals", "No model signal list available.")
    loser_signals = context.get("loser_signals", "No model signal list available.")

    if style == "beat writer notebook":
        return (
            f"{venue} sets the stage for {context['winner']} over {context['loser']}, and the conditions matter: {weather}. "
            f"The model sits at {context['confidence']} confidence with {context['data_points']} data-point leverage, which gives the pick real footing. "
            f"On the baseball side, the edge profile for {context['winner']} is driven by {winner_signals}. "
            f"The counter-case for {context['loser']} shows up in {loser_signals}, but the market signal ({movement}) still leans playable. "
            f"Umpire context ({ump}) is a late-variable worth watching, but this spot grades as a disciplined position rather than a flyer."
        )
    if style == "scouting report":
        return (
            f"Scouting read: {context['winning_pitcher']} vs {context['losing_pitcher']} favors {context['winner']} at {context['odds']}. "
            f"Model confidence ({context['confidence']}, data points {context['data_points']}) supports the same direction. "
            f"Signal stack for {context['winner']}: {winner_signals}. "
            f"Opposition signal stack for {context['loser']}: {loser_signals}. "
            f"Add weather ({weather}), umpire texture ({ump}), and line behavior ({movement}) and this profile stays actionable."
        )
    if style == "game-script breakdown":
        return (
            f"Game-script angle: {context['winner']} projects cleaner paths to control innings than {context['loser']}, starting with {context['winning_pitcher']} over {context['losing_pitcher']}. "
            f"The model calls it {context['confidence']} with {context['data_points']} data points and a listed number of {context['odds']}. "
            f"Early/ongoing pressure indicators for {context['winner']} show up in {winner_signals}. "
            f"Pushback factors for {context['loser']} are {loser_signals}. "
            f"Environment ({weather}), crew ({ump}), and market movement ({movement}) all point to the same side unless live conditions materially shift."
        )

    return (
        f"Price-first view: {context['winner']} over {context['loser']} at {context['odds']} with model confidence {context['confidence']} ({context['data_points']}). "
        f"The strongest support for {context['winner']} comes from: {winner_signals}. "
        f"The best resistance case for {context['loser']} comes from: {loser_signals}. "
        f"Venue/weather ({venue}, {weather}), umpire notes ({ump}), and market movement ({movement}) keep this in the value bucket."
    )


def _llm_commentary(context):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return _fallback_commentary(context)

    client = OpenAI(api_key=api_key)

    system = (
        "You are an MLB betting columnist writing warm, insightful pick commentary. "
        "Use provided facts only. Do not invent injuries, weather, umpires, or line movement. "
        "Blend model signals, matchup context, and market context naturally. "
        "Avoid repetitive openings and boilerplate phrasing across picks. "
        "If a field is unavailable, mention that briefly and move on. "
        "Write 5-7 sentences with clear baseball voice and actionable angle."
    )

    style_rotation = [
        "betting desk",
        "beat writer notebook",
        "scouting report",
        "game-script breakdown",
    ]
    style = style_rotation[(int(context.get("pick_index", 1)) - 1) % len(style_rotation)]

    style_instructions = {
        "betting desk": "Open with pricing/value. Focus on edge vs market and risk/reward framing.",
        "beat writer notebook": "Open with scene-setting baseball context (venue/conditions/mood) then actionable pick logic.",
        "scouting report": "Lead with pitcher/hitter profile and matchup traits, then connect to betting angle.",
        "game-script breakdown": "Project likely game flow (early innings, bullpen leverage, late-game path) and tie to the pick.",
    }
    style_hint = style_instructions.get(style, "Write with strong baseball context and clear pick rationale.")
    context["style"] = style

    user = (
        f"Pick: {context['winner']} over {context['loser']}\n"
        f"Writing Style Lens: {style}\n"
        f"Style Directive: {style_hint}\n"
        f"Odds: {context['odds']}\n"
        f"Confidence: {context['confidence']}\n"
        f"Data Points: {context['data_points']}\n"
        f"Winner Data Signals: {context['winner_signals']}\n"
        f"Loser Data Signals: {context['loser_signals']}\n"
        f"Venue: {context['venue']}\n"
        f"Weather: {context['weather_summary']}\n"
        f"Umpire Crew: {context['umpire_summary']}\n"
        f"Winner Injuries: {context['winner_injuries']}\n"
        f"Loser Injuries: {context['loser_injuries']}\n"
        f"Line Movement: {context['line_movement_text']}\n"
        f"Winning Pitcher: {context['winning_pitcher']}\n"
        f"Losing Pitcher: {context['losing_pitcher']}\n"
        "Do not reuse generic opener phrases from prior picks. Make this read distinct.\n"
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.75,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (resp.choices[0].message.content or "").strip() or _fallback_commentary(context)
    except Exception as e:
        print(f"LLM commentary failed for {context['winner']} vs {context['loser']}: {e}")
        return _fallback_commentary(context)


def write_daily_pick_markdown(predictions, odds_data, model_name):
    valid = [p for p in predictions if p.winning_team != '-']
    if not valid:
        return None

    eastern = pytz.timezone("US/Eastern")
    today = str(datetime.now(eastern).date())

    abbr_to_name, name_to_id = _get_team_maps()
    schedule = _build_schedule_lookup(today)

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

        odds_entry = odds_lookup.get(frozenset([winner_name, loser_name]))
        line_move = _extract_line_movement(odds_entry, winner_name)

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
            "winning_pitcher": p.winning_pitcher,
            "losing_pitcher": p.losing_pitcher,
        }

        commentary = _llm_commentary(context)

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
        lines.append(f"- **Line Movement:** {context['line_movement_text']}")
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
