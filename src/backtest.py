import datetime
import json
import os

# from src.analysis.pitching.pitchingevaluation import *
# from src.analysis.batting.battingevaluation import *
# from src.analysis.vs.vsevaluation import evaluate_vs_matchup
# from src.common.util import *
# from src.connector.stats import *
from datetime import date, timedelta, datetime
from time import sleep

import statsapi

from src import dutch
from src.common.objects import AdvantageScore, BacktestMetrics
from src.common.util import get_teams_list, select_winner, post_to_slack_backtest
from src.connector import slack
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
    if not os.path.exists(f"resources/odds/{date}.json"):
        get_odds_by_date(date)
    with open(f"resources/odds/{date}.json") as f:
        data = json.load(f)
    return format_odds_data(data)


def backtest_one_pick(model, model_hitting_fn, model_pitching_fn, model_vs_fn, start_date, end_date):
    metrics = 1000 #BacktestMetrics()

    delta = timedelta(days=1)
    # for each day april through september
    while start_date <= end_date:
        start_date_str = start_date.strftime("%m/%d/%Y")
        odds_date_str = start_date.strftime("%Y-%m-%d")
        odds_data = get_odds_data(odds_date_str)
        print(start_date_str)
        teams = get_teams_list()
        # get the schedule for the day
        games = get_schedule_by_date(odds_date_str)
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

        metrics = post_to_slack_backtest(start_date_str, winners, "dutch", metrics)
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


def daily(event, context):
    yesterday = (datetime.strptime(str(date.today()), '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    start_date = yesterday
    end_date = yesterday
    backtest_one_pick("dutch", dutch.hitting_backtest, dutch.pitching_backtest, dutch.vs_backtest, start_date, end_date)


def full():
    # first half
    start_date = date(2024, 4, 1)
    end_date = date(2024, 7, 14)
    backtest_one_pick("dutch", dutch.hitting_backtest, dutch.pitching_backtest, dutch.vs_backtest, start_date, end_date)
    bankroll = slack.post_backtest("All Star Break", "dutch")
    # second half
    start_date = date(2024, 7, 19)
    end_date = date(2024, 9, 30)
    backtest_one_pick("dutch", dutch.hitting_backtest, dutch.pitching_backtest, dutch.vs_backtest, start_date, end_date)


def adhoc(start_date, end_date):
    # first half
    backtest_one_pick("dutch", dutch.hitting_backtest, dutch.pitching_backtest, dutch.vs_backtest, start_date, end_date)


def main(event, context):
    start_time = datetime.now()
    # daily(event, context)
    # full()
    adhoc(date(2024, 10, 25), date(2024, 10, 25))
    end_time = datetime.now()
    print(f"Start time: {start_time}")
    print(f"End time: {end_time}")
    print(f"Execution time: {end_time - start_time}")


main('event', 'context')
