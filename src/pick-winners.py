from src.analysis.pitching import *
from src.analysis.batting import *
from src.common.util import *
from src.connector.sportsbook import *
from src.connector.stats import *
from src.connector.slack import *


def main():
    teams = get_teams_list()
    odds_data = get_odds()
    winners = []
    for team in teams:
        todays_game_list = get_todays_game(team.id)
        if len(todays_game_list) > 0:
            todays_game = todays_game_list.pop(0)
            game_id = todays_game['game_id']
            game_data = statsapi.get("game", {"gamePk": game_id})
            if todays_game['home_name'] == team.name:
                adv_score = AdvantageScore(0, 0)
                adv_score = evaluate_pitching_matchup(adv_score, game_data)
                adv_score = evaluate_hitting_matchup(adv_score, game_data)
                winners.append(select_winner(adv_score, game_data, odds_data))

    write_csv(winners)
    print_csv(winners)
    print_str(winners)
    post_to_slack(winners)


main()
