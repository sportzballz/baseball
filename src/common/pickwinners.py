from src.common.util import *
from src.connector.sportsbook import get_odds
from src.connector.stats import *
from src.common.objects import AdvantageScore


def main(model, model_hitting_fn, model_pitching_fn, model_vs_fn):
    teams = get_teams_list()
    odds_data = {"results": []}
    odds_data = get_odds()
    winners = []
    day = date.today()
    for team in teams:
        todays_games = get_todays_games(team.id, day)
        if len(todays_games) > 0:
            todays_game = todays_games[0]
            game_id = todays_game['game_id']
            game_data = statsapi.get("game", {"gamePk": game_id})

            if todays_game['home_name'] == team.name:
                home_stats = []
                away_stats = []
                adv_score = AdvantageScore(home=1, away=0, home_stats=home_stats, away_stats=away_stats)
                adv_score = model_hitting_fn(adv_score, game_data, model)
                adv_score = model_pitching_fn(adv_score, game_data, model)
                adv_score = model_vs_fn(adv_score, game_data, model)
                winners.append(select_winner(adv_score, game_data, odds_data))

    # write_csv(winners)
    # print_csv(winners)
    # print_str(winners)
    post_to_slack(winners, model)
