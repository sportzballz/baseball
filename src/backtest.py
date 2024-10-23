import datetime
import json
import os

# from src.analysis.pitching.pitchingevaluation import *
# from src.analysis.batting.battingevaluation import *
# from src.analysis.vs.vsevaluation import evaluate_vs_matchup
# from src.common.util import *
# from src.connector.stats import *
from datetime import date, timedelta
from time import sleep

import statsapi

from src import dutch
from src.common.objects import AdvantageScore
from src.common.util import get_teams_list, select_winner, post_to_slack_backtest
from src.connector.sportsbook import get_odds
from src.connector.sportsbookreview import get_odds_by_date
from src.connector.stats import get_schedule_by_date


def format_odds_data(odds_data):
    results = []
    game_rows = odds_data['props']['pageProps']['oddsTables'][0]['oddsTableModel']['gameRows']
    for game_row in game_rows:
        teams = {}
        moneyline = {}
        current = {}
        odds = []
        teams.update({"home": {"team": game_row['gameView']['homeTeam']['fullName']}})
        teams.update({"away": {"team": game_row['gameView']['awayTeam']['fullName']}})

        if game_row['openingLineViews'][0] is None:
            moneyline = {"moneyline": {"current": {"homeOdds": 100,"awayOdds": 100}}}
        else:
            moneyline = {"moneyline": {"current": {"homeOdds": game_row['openingLineViews'][0]['currentLine']['homeOdds'],"awayOdds": game_row['openingLineViews'][0]['currentLine']['awayOdds']}}}

        odds.append(moneyline)
        results.append({"teams": teams, "odds": odds})
    return {"results": results}


def get_odds_data(date):
    if not os.path.exists(f"resources/{date}.json"):
        get_odds_by_date(date)
    with open(f"resources/{date}.json") as f:
        data = json.load(f)
    return format_odds_data(data)


def backtest_one_pick(model, model_hitting_fn, model_pitching_fn, model_vs_fn, odds_data):
    bankroll = 27322.65
    start_date = date(2024, 4, 30)
    end_date = date(2024, 9, 30)
    delta = timedelta(days=1)
    # for each day april through september
    while start_date <= end_date:
        start_date_str = start_date.strftime("%m/%d/%Y")
        odds_date_str = start_date.strftime("%Y-%m-%d")
        odds_data = get_odds_data(odds_date_str)
        print(start_date_str)
        teams = get_teams_list()
        # get the schedule for the day
        games = get_schedule_by_date(start_date_str)
        # for each game in the schedule
        winners = []
        for game in games:
            print(game["game_id"])
            game_id = game['game_id']
            game_data = statsapi.get("game", {"gamePk": game_id})
            for team in teams:
                if game['home_name'] == team.name:
                    home_stats = []
                    away_stats = []
                    adv_score = AdvantageScore(home=1, away=0, home_stats=home_stats, away_stats=away_stats, home_lineup_available=True, away_lineup_available=True)

                    adv_score = model_hitting_fn(adv_score, game_data, str(start_date))
                    adv_score = model_pitching_fn(adv_score, game_data, str(start_date))
                    adv_score = model_vs_fn(adv_score, game_data, str(start_date))
                    winner = select_winner(adv_score, game_data, odds_data)
                    print(winner.to_string())
                    print(adv_score.to_string())
                    winners.append(winner)

        bankroll = post_to_slack_backtest(start_date_str, winners, "dutch", bankroll)
        start_date += delta


            # get the game data
            # pick the winner
            # add to winner list
    # find highest confidence pick
    # check if team with highest confidence pick won


def load_odds_data():
    start_date = date(2024, 7, 31)
    end_date = date(2024, 7, 31)
    delta = timedelta(days=1)
    current_date = start_date
    # for each day april through september
    while current_date <= end_date:
        current_date_str = current_date.strftime("%Y-%m-%d")
        get_odds_by_date(current_date_str)
        current_date += delta


def main(event, context):
    odds_data = {"results": []}
    # odds_data = get_odds()
    # load_odds_data()
    # odds_data = get_odds_by_date("2024-07-31")
    backtest_one_pick("dutch", dutch.hitting_backtest, dutch.pitching_backtest, dutch.vs_backtest, odds_data)
    # print(event)
    # model = os.environ['MODEL']
    # year = event['Records'][0]['messageAttributes']['year']['stringValue']
    # team_name = event['Records'][0]['messageAttributes']['team_name']['stringValue']
    # team_id = event['Records'][0]['messageAttributes']['team_id']['stringValue']
    #
    # odds_data = {"results": []}
    #
    # winning_count = 0
    # losing_count = 0
    # no_count = 0
    #
    # try:
    #     team_schedule = get_schedule_by_year(team_id, year)
    #     yesterdays_game_id = team_schedule[0]['game_id']
    #     yesterdays_game_data = statsapi.get("game", {"gamePk": yesterdays_game_id})
    #     try:
    #         for todays_game in team_schedule:
    #             game_id = todays_game['game_id']
    #             game_data = statsapi.get("game", {"gamePk": game_id})
    #             if todays_game['game_type'] == 'R' and todays_game['home_name'] == team_name:
    #                 try:
    #                     adv_score = AdvantageScore(0, 0)
    #                     adv_score = evaluate_pitching_matchup_backtest(adv_score, game_data)
    #                     adv_score = evaluate_hitting_matchup_backtest(adv_score, yesterdays_game_data)
    #                     # adv_score = evaluate_vs_matchup(adv_score, game_data)
    #                     projected_winner = select_winner(adv_score, game_data, odds_data).winning_team
    #                     actual_winner = todays_game['winning_team']
    #                     d = game_data['gameData']['datetime']['officialDate']
    #                     print(
    #                         f"Team: {team_name} Date: {d} Projected Winner: {projected_winner} | Actual Winner: {actual_winner}")
    #                     if projected_winner == '-' or actual_winner == '-':
    #                         no_count += 1
    #                     elif projected_winner == actual_winner:
    #                         winning_count += 1
    #                     else:
    #                         losing_count += 1
    #                 except Exception as e:
    #                     d = game_data['gameData']['datetime']['officialDate']
    #                     print(f'Error: {team_name} | {d} : {e}')
    #                     pass
    #             yesterdays_game_data = game_data
    #     except Exception as e:
    #         print(f'Error: {team_name} : {e}')
    #         pass
    # except Exception as e:
    #     print(f'Error: {e}')
    #     pass
    #
    # tally = f"Winning Count: {winning_count} | Losing Count: {losing_count} | No Pick Count: {no_count}"
    # post_to_slack_backtest(tally, year, team_name)
main('event', 'context')
