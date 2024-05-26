from src.common.util import *
from src.connector.stats import *


def main(model, model_hitting_fn, model_pitching_fn):
    teams = get_teams_list()
    #odds_data = get_odds()
    odds_data = {"results": []}
    winners = []
    day = date.today()
    for team in teams:
        todays_games = get_todays_games(team.id, day)
        if len(todays_games) > 0:
            todays_game = todays_games[0]
            game_id = todays_game['game_id']
            game_data = statsapi.get("game", {"gamePk": game_id})

            if todays_game['home_name'] == team.name:
                adv_score = AdvantageScore(home=1, away=0)#homfield advantage
                adv_score = model_hitting_fn(adv_score, game_data, model)
                adv_score = model_pitching_fn(adv_score, game_data, model)
                # adv_score = model_pitching_fn(adv_score, game_data)
                winners.append(select_winner(adv_score, game_data, odds_data))

    # write_csv(winners)
    # print_csv(winners)
    # print_str(winners)
    post_to_slack(winners, model)
