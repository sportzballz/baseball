import time

import statsapi
from src.common.objects import *
from datetime import datetime
from datetime import timezone
import pytz
from src.connector import slack
from src.connector.stats import *


def get_teams():
    ari = statsapi.lookup_team('dia')
    atl = statsapi.lookup_team('atl')
    bal = statsapi.lookup_team('bal')
    bos = statsapi.lookup_team('bos')
    chc = statsapi.lookup_team('chn')
    chw = statsapi.lookup_team('cha')
    cin = statsapi.lookup_team('cin')
    cle = statsapi.lookup_team('cle')
    col = statsapi.lookup_team('col')
    det = statsapi.lookup_team('det')
    hou = statsapi.lookup_team('hou')
    kc = statsapi.lookup_team('kc')
    laa = statsapi.lookup_team('ana')
    lad = statsapi.lookup_team('lad')
    mia = statsapi.lookup_team('mia')
    mil = statsapi.lookup_team('mil')
    min = statsapi.lookup_team('min')
    nym = statsapi.lookup_team('nym')
    nyy = statsapi.lookup_team('nyy')
    oak = statsapi.lookup_team('oak')
    phi = statsapi.lookup_team('phi')
    pit = statsapi.lookup_team('pit')
    sd = statsapi.lookup_team('sd')
    sf = statsapi.lookup_team('sf')
    sea = statsapi.lookup_team('sea')
    stl = statsapi.lookup_team('stl')
    tb = statsapi.lookup_team('tb')
    tex = statsapi.lookup_team('tex')
    tor = statsapi.lookup_team('tor')
    wsh = statsapi.lookup_team('nat')


def get_teams_dict():
    teams_dict = {}
    teams = get_teams_list()
    for team in teams:
        teams_dict[team.name] = team.abbreviation
    return teams_dict


def get_team_ids_dict():
    teams_dict = {}
    teams = get_teams_list()
    for team in teams:
        teams_dict[team.name] = team.id
    return teams_dict


def get_teams_list():
    teams_list = [
        Team('ari', 109, "Arizona Diamondbacks"),
        Team('atl', 144, "Atlanta Braves"),
        Team('bal', 110, "Baltimore Orioles"),
        Team('bos', 111, "Boston Red Sox"),
        Team('chc', 112, "Chicago Cubs"),
        Team('chw', 145, "Chicago White Sox"),
        Team('cin', 113, "Cincinnati Reds"),
        Team('cle', 114, "Cleveland Guardians"),
        Team('col', 115, "Colorado Rockies"),
        Team('det', 116, "Detroit Tigers"),
        Team('hou', 117, "Houston Astros"),
        Team('kc ', 118, "Kansas City Royals"),
        Team('laa', 108, "Los Angeles Angels"),
        Team('lad', 119, "Los Angeles Dodgers"),
        Team('mia', 146, "Miami Marlins"),
        Team('mil', 158, "Milwaukee Brewers"),
        Team('min', 142, "Minnesota Twins"),
        Team('nym', 121, "New York Mets"),
        Team('nyy', 147, "New York Yankees"),
        Team('oak', 133, "Oakland Athletics"),
        Team('phi', 143, "Philadelphia Phillies"),
        Team('pit', 134, "Pittsburgh Pirates"),
        Team('sd ', 135, "San Diego Padres"),
        Team('sf ', 137, "San Francisco Giants"),
        Team('sea', 136, "Seattle Mariners"),
        Team('stl', 138, "St. Louis Cardinals"),
        Team('tb ', 139, "Tampa Bay Rays"),
        Team('tex', 140, "Texas Rangers"),
        Team('tor', 141, "Toronto Blue Jays"),
        Team('wsh', 120, "Washington Nationals")
    ]
    return teams_list


def get_stat(team, stat, weight=1.0):
    try:
        return float(team.get(stat)) * float(weight)
    except Exception:
        return 0.0


def evaluate_stat(adv_score, home, away, stat, weight):
    home_stat = get_stat(home, stat, weight.weight)
    away_stat = get_stat(away, stat, weight.weight)
    if weight.lower_is_better:
        if home_stat < away_stat:
            return increase_home_advantage(adv_score, stat)
        elif away_stat < home_stat:
            return increase_away_advantage(adv_score, stat)
        else:
            return adv_score
    else:
        if home_stat > away_stat:
            return increase_home_advantage(adv_score, stat)
        elif away_stat > home_stat:
            return increase_away_advantage(adv_score, stat)
        else:
            return adv_score


def get_last_game_data(team_id, year, current_game_id):
    team_schedule = get_schedule_by_year(team_id, year)
    yesterdays_game_id = team_schedule[0]['game_id']
    for game in team_schedule:
        if game['game_id'] == current_game_id:
            return statsapi.get("game", {"gamePk": yesterdays_game_id})
        else:
            yesterdays_game_id = game['game_id']
    print("shouldn't get here")
    return statsapi.get("game", {"gamePk": yesterdays_game_id})


def get_todays_starting_lineup_profile(lineup):
    lineup_profile = []
    for player in lineup:
        lineup_profile.append(
            statsapi.player_stat_data(player.player_id, group="[hitting]", type="season", sportId=1))
    return lineup_profile


def get_lineup_profile(lineup):
    lineup_profile = []
    for player in lineup[1:]:
        lineup_profile.append(
            statsapi.player_stat_data(player['personId'], group="[hitting]", type="season", sportId=1))
    return lineup_profile


def get_lineup_profile_by_date(lineup, d):
    lineup_profile = []
    for player in lineup[1:]:
        lineup_profile.append(get_hitter_stats_by_date(player['personId'], d))
    return lineup_profile


def get_standard_weighted_stat(lineup, stat1, weight):
    weighted_avg = 0.0
    for player in lineup:
        s = player['stats'][0]['stats'][stat1]
        weighted_avg += float(weight) * float(s)
    return weighted_avg


def get_player_weighted_stat(lineup, stat1, stat2, test=False):
    weighted_avg = 0.0
    for player in lineup:
        try:
            if test:
                split_count = len(player['stats'][0]['splits'])
                ab = player['stats'][0]['splits'][split_count - 1]['stat'][stat2]
                s = player['stats'][0]['splits'][split_count - 1]['stat'][stat1]
            else:
                ab = player['stats'][0]['stats'][stat2]
                s = player['stats'][0]['stats'][stat1]
            weighted_avg += float(ab) / float(s)
        except Exception:
            pass
    print(stat1 + ": " + str(weighted_avg))
    return weighted_avg


def evaluate_player_weighted_stat(adv_score, home, away, stat1, stat2, lower_is_better=False, test=False):
    home_weighted_avg = get_player_weighted_stat(home, stat1, stat2, test)
    away_weighted_avg = get_player_weighted_stat(away, stat1, stat2, test)
    if lower_is_better:
        if home_weighted_avg < away_weighted_avg:
            return increase_home_advantage(adv_score, stat1)
        elif away_weighted_avg < home_weighted_avg:
            return increase_away_advantage(adv_score, stat1)
        else:
            return adv_score
    else:
        if home_weighted_avg > away_weighted_avg:
            return increase_home_advantage(adv_score, stat1)
        elif away_weighted_avg > home_weighted_avg:
            return increase_away_advantage(adv_score, stat1)
        else:
            return adv_score


def evaluate_standard_weighted_stat(adv_score, home, away, stat1, weight, lower_is_better=False):
    home_weighted_avg = get_standard_weighted_stat(home, stat1, weight)
    away_weighted_avg = get_standard_weighted_stat(away, stat1, weight)
    if lower_is_better:
        if home_weighted_avg < away_weighted_avg:
            return increase_home_advantage(adv_score, stat1)
        elif away_weighted_avg < home_weighted_avg:
            return increase_away_advantage(adv_score, stat1)
        else:
            return adv_score
    else:
        if home_weighted_avg > away_weighted_avg:
            return increase_home_advantage(adv_score, stat1)
        elif away_weighted_avg > home_weighted_avg:
            return increase_away_advantage(adv_score, stat1)
        else:
            return adv_score


def increase_home_advantage(adv_score, stat):
    adv_score.home_stats.append(stat)
    return AdvantageScore(adv_score.home + 1, adv_score.away, adv_score.home_stats, adv_score.away_stats, adv_score.home_lineup_available, adv_score.away_lineup_available)


def increase_away_advantage(adv_score, stat):
    adv_score.away_stats.append(stat)
    return AdvantageScore(adv_score.home, adv_score.away + 1, adv_score.home_stats, adv_score.away_stats, adv_score.home_lineup_available, adv_score.away_lineup_available)


def write_csv(winners):
    today = str(date.today())
    with open(f'./picks/{today}.csv', 'w') as f:
        f.write(',Odds,Winning Team,Losing Team,Date,Winning Pitcher\n')
        for winner in winners:
            if winner.winning_team != '-':
                f.write(winner.get_csv() + '\n')


def print_csv(winners):
    print('\n\n########## CSV\n')
    for winner in winners:
        if winner.winning_team != '-':
            winner.to_csv()


def print_str(winners):
    print('\n\n########## STR\n')
    for winner in winners:
        if winner.winning_team != '-':
            winner.print_string()


def post_to_slack_backtest(msg, model):
    slack.post_backtest("```" + msg + "```", model)


def post_to_slack(winners, model):
    slack.post(str(date.today()), model)
    highest_confidence = 0.000
    todays_pick = [Prediction('-', '-', '-', '-', '-', '-', '-', 0, '-', '0/0')]
    try:
        for winner in winners:
            if winner.winning_team != '-':
                if float(winner.confidence) >= highest_confidence:
                    if highest_confidence == float(winner.confidence):
                        todays_pick.append(winner)
                    else:
                        highest_confidence = float(winner.confidence)
                        todays_pick = [winner]
                slack.post(winner.to_string(), model)
                time.sleep(1)
    except ValueError:
        slack.post(winner.to_string(), model)
    for pick in todays_pick:
        if "----" not in str(pick.odds) and "." not in pick.winning_team and "." not in pick.losing_team:
            slack.post_todays_pick(str(date.today()) + " - " + model, model)
            slack.post_todays_pick(pick.to_string(), model)


def post_to_slack_backtest(d, winners, model):
    # slack.post_backtest(str(d), model)
    highest_confidence = 0.000
    todays_pick = [Prediction('-', '-', '-', '-', '-', '-', '-', 0, '-', '0/0')]
    try:
        for winner in winners:
            if winner.winning_team != '-':
                if float(winner.confidence) >= highest_confidence:
                    if highest_confidence == float(winner.confidence):
                        todays_pick.append(winner)
                    else:
                        highest_confidence = float(winner.confidence)
                        todays_pick = [winner]
                # slack.post_backtest(winner.to_string(), model)
                # time.sleep(1)
    except ValueError:
        # slack.post_backtest(winner.to_string(), model)
        print("exception")

    for pick in todays_pick:
        if "." not in pick.winning_team and "." not in pick.losing_team:
        # if "----" not in pick.odds and "." not in pick.winning_team and "." not in pick.losing_team:
            if "$" in pick.winning_team:
                slack.post_todays_pick_backtest(":white_check_mark:" + str(d) + " " + pick.to_string(), model)
            else:
                slack.post_todays_pick_backtest(":x:" + str(d) + " " + pick.to_string(), model)


def select_winner(adv_score, game_data, odds_data):
    print(f'select winner: {adv_score.to_string()}')
    teams_dict = get_teams_dict()
    try:
        est = pytz.timezone('US/Eastern')
        utc = pytz.utc
        game_date = game_data['gameData']['datetime']['officialDate']
        game_time = game_data['gameData']['datetime']['dateTime']
        ampm = game_data['gameData']['datetime']['ampm']
        dt_game_time = utc.localize(datetime.fromisoformat(game_time[:-1]))
        game_time = dt_game_time.astimezone(est).strftime('%I:%M')

        if adv_score.home >= adv_score.away:
            confidence = '{:1.3f}'.format(
                round((adv_score.home - adv_score.away) / (adv_score.home + adv_score.away), 3))
            data_points = f"{adv_score.home}/{adv_score.home + adv_score.away}"
            winning_team = game_data['gameData']['teams']['home']['name']
            winning_abbrv = teams_dict[winning_team] + "*"
            losing_team = game_data['gameData']['teams']['away']['name']
            losing_abbrv = teams_dict[losing_team]
            winning_pitcher = game_data['gameData']['probablePitchers']['home']['fullName']
            losing_pitcher = game_data['gameData']['probablePitchers']['away']['fullName']
            if not adv_score.home_lineup_available:
                winning_abbrv = '.' + winning_abbrv
            if not adv_score.away_lineup_available:
                losing_abbrv = '.' + losing_abbrv
            if game_data["liveData"]["linescore"]["teams"]["home"]["runs"] > game_data["liveData"]["linescore"]["teams"]["away"]["runs"]:
                winning_abbrv = '$' + winning_abbrv
            else:
                losing_abbrv = '$' + losing_abbrv
            for result in odds_data['results']:
                if result['teams']['home']['team'] == winning_team:
                    if len(result['odds']) > 0:
                        odds = result['odds'][0]['moneyline']['current']['homeOdds']
                    else:
                        odds = 0
                    print(
                        f"Odds: {odds}, Confidence: {confidence}, Data Points: {data_points}, Winning Team: {winning_team}, Losing Team: {losing_team}, Winning Pitcher: {winning_pitcher}, Losing Pitcher: {losing_pitcher}, Game Date: {game_date}, Game Time: {game_time}, AM/PM: {ampm}, Winning Stats: {adv_score.home_stats}, Losing Stats: {adv_score.away_stats}")
                    return Prediction(winning_abbrv, losing_abbrv, winning_pitcher, losing_pitcher, game_date,
                                      game_time, ampm, odds,
                                      confidence, data_points)
            print(
                f"Confidence: {confidence}, Data Points: {data_points}, Winning Team: {winning_team}, Losing Team: {losing_team}, Winning Pitcher: {winning_pitcher}, Losing Pitcher: {losing_pitcher}, Game Date: {game_date}, Game Time: {game_time}, AM/PM: {ampm}, Winning Stats: {adv_score.home_stats}, Losing Stats: {adv_score.away_stats}")
            return Prediction(winning_abbrv, losing_abbrv, winning_pitcher, losing_pitcher, game_date, game_time, ampm,
                              0, confidence,
                              data_points)
        elif adv_score.away > adv_score.home:
            confidence = '{:1.3f}'.format(
                round((adv_score.away - adv_score.home) / (adv_score.away + adv_score.home), 3))
            data_points = f"{adv_score.away}/{adv_score.home + adv_score.away}"
            winning_team = game_data['gameData']['teams']['away']['name']
            winning_abbrv = teams_dict[winning_team]
            losing_team = game_data['gameData']['teams']['home']['name']
            losing_abbrv = teams_dict[losing_team] + "*"
            winning_pitcher = game_data['gameData']['probablePitchers']['away']['fullName']
            losing_pitcher = game_data['gameData']['probablePitchers']['home']['fullName']
            if not adv_score.home_lineup_available:
                losing_abbrv = '.' + losing_abbrv
            if not adv_score.away_lineup_available:
                winning_abbrv = '.' + winning_abbrv
            if game_data["liveData"]["linescore"]["teams"]["home"]["runs"] > game_data["liveData"]["linescore"]["teams"]["away"]["runs"]:
                winning_abbrv = '$' + winning_abbrv
            else:
                losing_abbrv = '$' + losing_abbrv
            for result in odds_data['results']:
                if result['teams']['away']['team'] == winning_team:
                    if len(result['odds']) > 0:
                        odds = result['odds'][0]['moneyline']['current']['awayOdds']
                    else:
                        odds = 0
                    print(
                        f"Odds: {odds}, Confidence: {confidence}, Data Points: {data_points}, Winning Team: {winning_team}, Losing Team: {losing_team}, Winning Pitcher: {winning_pitcher}, Losing Pitcher: {losing_pitcher}, Game Date: {game_date}, Game Time: {game_time}, AM/PM: {ampm}, Winning Stats: {adv_score.away_stats}, Losing Stats: {adv_score.home_stats}")
                    return Prediction(winning_abbrv, losing_abbrv, winning_pitcher, losing_pitcher, game_date,
                                      game_time, ampm, odds,
                                      confidence, data_points)
            print(
                f"Confidence: {confidence}, Data Points: {data_points}, Winning Team: {winning_team}, Losing Team: {losing_team}, Winning Pitcher: {winning_pitcher}, Losing Pitcher: {losing_pitcher}, Game Date: {game_date}, Game Time: {game_time}, AM/PM: {ampm}, Winning Stats: {adv_score.away_stats}, Losing Stats: {adv_score.home_stats}")
            return Prediction(winning_abbrv, losing_abbrv, winning_pitcher, losing_pitcher, game_date, game_time, ampm, 0,
                              confidence,
                              data_points)
        else:
            away_team = game_data['gameData']['teams']['away']['name']
            away_abbrv = teams_dict[away_team]
            home_team = game_data['gameData']['teams']['home']['name']
            home_abbrv = teams_dict[home_team] + "*"
            # print(f"No advantage in {away_abbrv} at {home_abbrv} on {game_date}")
            return Prediction('-', '-', '-', '-', game_date, game_time, ampm, 0, 0, 0)
    except Exception as e:
        print(e)
        return Prediction('-', '-', '-', '-', game_date, game_time, ampm, 0, 0, 0)
