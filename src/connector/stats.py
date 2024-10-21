import statsapi
# from pybaseball import *
# import pandas as pd

import requests
import json

from datetime import datetime, date, timedelta


# def pybaseball_statcast(start_dt, end_dt):
#     # s = statcast(start_dt="2019-06-24", end_dt="2019-06-25").columns
#     df = statcast_batter('2008-07-15', '2017-07-15', player_id = 120074)
#     pitch_types = df.pitch_type
#     print(pitch_types)
#     t = df.head(n=2)
#     print(df.columns)
#     print(t)
#     return df



def get_pitcher_stats(player_id):
    return statsapi.player_stat_data(personId=player_id, group='pitching', type='season')


def get_pitcher_stats_by_date(player_id, d):
    year = d[:4]
    s = f"{year}-01-01"
    stmp = datetime.strptime(s, "%Y-%m-%d")
    etmp = datetime.strptime(d, "%Y-%m-%d")
    start = stmp.strftime("%m/%d/%Y")
    end = etmp.strftime("%m/%d/%Y")
    url = f'https://statsapi.mlb.com/api/v1/people/{player_id}?hydrate=stats(group=[pitching],type=[byDateRange],startDate={start},endDate={end},season={year})'
    resp = requests.get(url)
    rjson = json.loads(resp.text)
    return rjson['people'][0]


def get_hitter_stats_by_date(player_id, d):
    year = d[:4]
    s = f"{year}-01-01"
    stmp = datetime.strptime(s, "%Y-%m-%d")
    etmp = datetime.strptime(d, "%Y-%m-%d")
    start = stmp.strftime("%m/%d/%Y")
    end = etmp.strftime("%m/%d/%Y")
    url = f'https://statsapi.mlb.com/api/v1/people/{player_id}?hydrate=stats(group=[hitting],type=[byDateRange],startDate={start},endDate={end},season={year})'
    resp = requests.get(url)
    rjson = json.loads(resp.text)
    return rjson['people'][0]


def get_todays_games(team_id, day):
    return statsapi.schedule(date=day, team=team_id)


def get_schedule_by_date(d):
    retval = statsapi.schedule(start_date=d, end_date=d)
    return retval


def get_schedule_by_year(team_id, year):
    start = f"{year}-01-01"
    end = f"{year}-12-31"
    retval = statsapi.schedule(start_date=start, end_date=end, team=team_id)
    return retval


def get_team_data(team_id):
    return statsapi.get("team", {"teamId": team_id})


def get_home_batters_by_gameid(game_id):
    return statsapi.boxscore_data(game_id)['homeBatters']


def get_away_batters_by_gameid(game_id):
    return statsapi.boxscore_data(game_id)['awayBatters']


def get_home_batting_total_by_game_id(game_id):
    return statsapi.boxscore_data(game_id)['homeBattingTotals']


def get_away_batting_total_by_game_id(game_id):
    return statsapi.boxscore_data(game_id)['awayBattingTotals']


def get_last_game_batters(team_id):
    last_game_id = statsapi.last_game(team_id)
    last_boxscore = statsapi.boxscore_data(last_game_id)
    lbs = json.dumps(last_boxscore)
    if last_boxscore['teamInfo']['home']['id'] == team_id:
        return last_boxscore['homeBatters']
    else:
        return last_boxscore['awayBatters']


def get_lineup_batting_totals(lineup):
    dt = date.today().strftime("%Y-%m-%d")
    for player in lineup:
        stats = statsapi.player_stat_data(player.player_id, group="[hitting]", type="season", sportId=1)
        print(stats)


def get_last_game_by_date(team_id, d):
    while(1):
        delta = timedelta(days=1)
        d -= delta
        games = get_schedule_by_date(d)
        for game in games:
            if game['home_id'] == team_id or game['away_id'] == team_id:
                game_id = game['game_id']
                return game_id
                break


def get_last_game_batting_totals(team_id):
    last_game_id = statsapi.last_game(team_id)
    last_boxscore = statsapi.boxscore_data(last_game_id)
    if last_boxscore['teamInfo']['home']['id'] == team_id:
        return last_boxscore['homeBattingTotals']
    else:
        return last_boxscore['awayBattingTotals']


def get_game(game_id):
    return statsapi.boxscore_data(game_id)


def get_vs_games(home, away):
    year = date.today().year
    start_date = f'04/01/{year}'
    end_date = date.today().strftime("%m/%d/%Y")
    games = statsapi.schedule(start_date=start_date, end_date=end_date, team=home, opponent=away)
    return games


def get_vs_game_ids_before_date(home, away, d):
    game_id_list = []
    year = date.today().year
    start_date = f'04/01/{year}'
    end_date = str(d)
    games = statsapi.schedule(start_date=start_date, end_date=end_date, team=home, opponent=away)
    for game in games:
        game_id_list.append(game['game_id'])
    return game_id_list

def get_vs_game_ids(home, away):
    game_id_list = []
    year = date.today().year
    start_date = f'04/01/{year}'
    end_date = date.today().strftime("%m/%d/%Y")
    games = statsapi.schedule(start_date=start_date, end_date=end_date, team=home, opponent=away)
    for game in games:
        game_id_list.append(game['game_id'])
    return game_id_list


def get_game_contextMetrics(game_pk):
    return statsapi.get("game_contextMetrics", {"gamePk": game_pk})


def get_game_winProbability(game_pk):
    return statsapi.get("game_winProbability", {"gamePk": game_pk})