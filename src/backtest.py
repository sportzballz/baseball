import datetime

from src.analysis.pitching.pitchingevaluation import *
from src.analysis.batting.battingevaluation import *
from src.analysis.vs.vsevaluation import evaluate_vs_matchup
from src.common.util import *
from src.connector.stats import *


def main(event, context):
    print(event)
    year = event['Records'][0]['messageAttributes']['year']['stringValue']
    team_name = event['Records'][0]['messageAttributes']['team_name']['stringValue']
    team_id = event['Records'][0]['messageAttributes']['team_id']['stringValue']

    odds_data = {"results": []}

    winning_count = 0
    losing_count = 0
    no_count = 0

    try:
        team_schedule = get_schedule_by_year(team_id, year)
        yesterdays_game_id = team_schedule[0]['game_id']
        yesterdays_game_data = statsapi.get("game", {"gamePk": yesterdays_game_id})
        try:
            for todays_game in team_schedule:
                game_id = todays_game['game_id']
                game_data = statsapi.get("game", {"gamePk": game_id})
                if todays_game['game_type'] == 'R' and todays_game['home_name'] == team_name:
                    try:
                        adv_score = AdvantageScore(0, 0)
                        adv_score = evaluate_pitching_matchup_backtest(adv_score, game_data)
                        adv_score = evaluate_hitting_matchup_backtest(adv_score, yesterdays_game_data)
                        # adv_score = evaluate_vs_matchup(adv_score, game_data)
                        projected_winner = select_winner(adv_score, game_data, odds_data).winning_team
                        actual_winner = todays_game['winning_team']
                        d = game_data['gameData']['datetime']['officialDate']
                        print(
                            f"Team: {team_name} Date: {d} Projected Winner: {projected_winner} | Actual Winner: {actual_winner}")
                        if projected_winner == '-' or actual_winner == '-':
                            no_count += 1
                        elif projected_winner == actual_winner:
                            winning_count += 1
                        else:
                            losing_count += 1
                    except Exception as e:
                        d = game_data['gameData']['datetime']['officialDate']
                        print(f'Error: {team_name} | {d} : {e}')
                        pass
                yesterdays_game_data = game_data
        except Exception as e:
            print(f'Error: {team_name} : {e}')
            pass
    except Exception as e:
        print(f'Error: {e}')
        pass

    tally = f"Winning Count: {winning_count} | Losing Count: {losing_count} | No Pick Count: {no_count}"
    post_to_slack_backtest(tally, year, team_name)
