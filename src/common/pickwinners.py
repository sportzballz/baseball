

import os
from  common.util import *
from  connector.sportsbook import get_odds
from  connector.stats import *
from  connector.mlbstartinglineups import *
from connector.pick_markdown import write_daily_pick_markdown
from connector.pick_site_publish import publish_daily_site
from  common.objects import AdvantageScore


def main(model, model_hitting_fn, model_pitching_fn, model_vs_fn):
    teams = get_teams_list()
    lineups = get_starting_lineups()

    odds_data = get_odds()
    # odds_data = {'results': []}

    winners = []
    day = datetime.now(pytz.timezone('US/Eastern')).date()
    for team in teams:
        if team.name == 'Athletics':
            pass
        todays_games = get_todays_games(team.id, day)
        print(f'{team.name} will play {len(todays_games)} games today')
        # if len(todays_games) > 0:
        for todays_game in todays_games:
            game_id = todays_game['game_id']
            game_data = statsapi.get("game", {"gamePk": game_id})

            if todays_game['home_name'] == team.name:
                home_stats = []
                away_stats = []
                adv_score = AdvantageScore(home=1, away=0, home_stats=home_stats, away_stats=away_stats, home_lineup_available=False, away_lineup_available=False)
                adv_score = model_hitting_fn(adv_score, game_data, model, lineups)
                adv_score = model_pitching_fn(adv_score, game_data, model, lineups)
                adv_score = model_vs_fn(adv_score, game_data, model, lineups)
                winners.append(select_winner(adv_score, game_data, odds_data))
                print(adv_score.to_string())

    # write_csv(winners)
    # print_csv(winners)
    # print_str(winners)

    runtime_mode = os.environ.get("BASEBALL_RUNTIME_MODE", "").strip().lower()
    in_aws_lambda = bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME")) or os.environ.get(
        "AWS_EXECUTION_ENV", ""
    ).startswith("AWS_Lambda")

    if runtime_mode == "lambda":
        effective_mode = "lambda"
    elif runtime_mode == "local":
        effective_mode = "local"
    elif runtime_mode == "both":
        effective_mode = "both"
    else:
        # Auto mode: lambda environments do Slack-only; everything else does local LLM/html-only.
        effective_mode = "lambda" if in_aws_lambda else "local"

    print(f"Baseball runtime mode: {effective_mode}")

    if effective_mode in ("lambda", "both"):
        try:
            post_to_slack(winners, model)
        except Exception as e:
            print(f"Slack post failed (continuing): {e}")
    else:
        print("Skipping Slack posting in local mode")

    if effective_mode in ("local", "both"):
        # Write rich daily markdown commentary (weather, umpires, injuries, line movement)
        try:
            output_path = write_daily_pick_markdown(winners, odds_data, model)
            if output_path:
                print(f"Wrote pick commentary: {output_path}")

                # Auto-publish to sportzballz.io as yyyy-mm-dd.html + refresh top-level index
                try:
                    site_repo = os.environ.get('SPORTZBALLZ_SITE_REPO')
                    published_path = publish_daily_site(output_path, site_repo)
                    if published_path:
                        print(f"Published picks page: {published_path}")
                except Exception as pe:
                    print(f"Failed to publish picks site: {pe}")
        except Exception as e:
            print(f"Failed to write markdown commentary: {e}")
    else:
        print("Skipping markdown/html generation in lambda mode")
