from src.analysis.pitching.pitchingevaluation import *
from src.analysis.batting.battingevaluation import *
from src.analysis.vs.vsevaluation import evaluate_vs_matchup
from src.common.util import *
from src.connector.stats import *
from src.pickwinners import main
import sys


def test(run_type, year):
    if run_type == 'today':
        main(None, None)
    else:
        teams = get_teams_list()
        odds_data = {"results": []}

        winners = []
        winning_count = 0
        losing_count = 0

        for team in teams:
            team_schedule = get_schedule_by_year(team.id, year)
            for todays_game in team_schedule:
                if todays_game['game_type'] == 'R':
                    game_id = todays_game['game_id']
                    game_data = statsapi.get("game", {"gamePk": game_id})

                    if todays_game['home_name'] == team.name:
                        adv_score = AdvantageScore(0, 0)
                        adv_score = evaluate_pitching_matchup(adv_score, game_data, test=True)
                        adv_score = evaluate_hitting_matchup(adv_score, game_data, test=True)
                        # adv_score = evaluate_vs_matchup(adv_score, game_data)
                        projected_winner = select_winner(adv_score, game_data, odds_data).winning_team
                        actual_winner = todays_game['winning_team']
                        print(f"Projected Winner: {projected_winner} | Actual Winner: {actual_winner}")
                        if projected_winner == actual_winner:
                            winning_count += 1
                        else:
                            losing_count += 1

        # write_csv(winners)
        # print_csv(winners)
        print(f"Winning Count: {winning_count} | Losing Count: {losing_count}")
        print_str(winners)
        # post_to_slack(winners)


test(sys.argv[1],sys.argv[2])
