import datetime
import os

from src.analysis.pitchingevaluation import *
from src.analysis.battingevaluation import *
from src.common.util import *
from src.connector.stats import *
from src.pickwinners import main
import sys
from datetime import datetime


def test(run_type, year):
    model = os.environ['MODEL']
    if run_type == 'today':
        main(None, None)
    else:
        start_time = datetime.now()
        print(f'Start Time: {start_time}')
        teams = get_teams_list()
        odds_data = {"results": []}

        winners = []
        winning_count = 0
        losing_count = 0
        no_count = 0

        for team in teams:
            try:
                team_schedule = get_schedule_by_year(team.id, year)
                yesterdays_game_id = team_schedule[0]['game_id']
                yesterdays_game_data = statsapi.get("game", {"gamePk": yesterdays_game_id})
                # cm = get_game_contextMetrics(yesterdays_game_id)

                try:
                    for todays_game in team_schedule:
                        game_id = todays_game['game_id']
                        game_data = statsapi.get("game", {"gamePk": game_id})
                        if todays_game['game_type'] == 'R' and todays_game['home_name'] == team.name:
                            try:
                                wp = get_game_winProbability(game_id)
                                print(wp)
                                adv_score = AdvantageScore(0, 0)
                                adv_score = evaluate_pitching_matchup_backtest(adv_score, game_data)
                                adv_score = evaluate_hitting_matchup_backtest(adv_score, yesterdays_game_data)
                                # adv_score = evaluate_vs_matchup(adv_score, game_data)
                                projected_winner = select_winner(adv_score, game_data, odds_data).winning_team
                                actual_winner = todays_game['winning_team']
                                d = game_data['gameData']['datetime']['officialDate']
                                print(f"Team: {team.name} Date: {d} Projected Winner: {projected_winner} | Actual Winner: {actual_winner}")
                                if projected_winner == '-' or actual_winner == '-':
                                    no_count += 1
                                elif projected_winner == actual_winner:
                                    winning_count += 1
                                else:
                                    losing_count += 1
                            except Exception as e:
                                d = game_data['gameData']['datetime']['officialDate']
                                print(f'Error: {team.name} | {d} : {e}')
                                pass
                        yesterdays_game_data = game_data
                except Exception as e:
                    print(f'Error: {team.name} : {e}')
                    pass
            except Exception as e:
                pass

        # write_csv(winners)
        # print_csv(winners)
        print(f"Winning Count: {winning_count} | Losing Count: {losing_count} | No Pick Count: {no_count}")
        end_time = datetime.now()
        print(f'End Time: {end_time}')
        print(f'Time Elapsed: {end_time - start_time}')

        # print_str(winners)
        # post_to_slack(winners)


test(sys.argv[1],sys.argv[2])
