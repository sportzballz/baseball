import statsapi
from src.common.objects import *
from datetime import date
from src.connector import slack


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
    teams_dict = {
        'ari': 109,
        'atl': 144,
        'bal': 110,
        'bos': 111,
        'chc': 112,
        'chw': 145,
        'cin': 113,
        'cle': 114,
        'col': 115,
        'det': 116,
        'hou': 117,
        'kc': 118,
        'laa': 108,
        'lad': 143,
        'mia': 146,
        'mil': 158,
        'min': 142,
        'nym': 121,
        'nyy': 147,
        'oak': 133,
        'phi': 143,
        'pit': 134,
        'sd': 135,
        'sf': 137,
        'sea': 136,
        'stl': 138,
        'tb': 139,
        'tex': 140,
        'tor': 141,
        'wsh': 120
    }
    return teams_dict


def get_teams_list():
    teams_list = [
        Team('ari', 109, "Arizona Diamondbacks"),
        Team('atl', 144, "Atlanta Braves"),
        Team('bal', 110, "Baltimore Orioles"),
        Team('bos', 111, "Boston Red Sox"),
        Team('chc', 112, "Chicago Cubs"),
        Team('chw', 145, "Chicago White Sox"),
        Team('cin', 113, "Cincinatti Reds"),
        Team('cle', 114, "Cleveland Guardians"),
        Team('col', 115, "Colorado Rockies"),
        Team('det', 116, "Detroit Tigers"),
        Team('hou', 117, "Houston Astros"),
        Team('kc', 118, "Kansas City Royals"),
        Team('laa', 108, "Los Angeles Angels"),
        Team('lad', 143, "Los Angeles Dodgers"),
        Team('mia', 146, "Miami Marlins"),
        Team('mil', 158, "Milwaukee Brewers"),
        Team('min', 142, "Minnesota Twins"),
        Team('nym', 121, "New York Mets"),
        Team('nyy', 147, "New York Yankees"),
        Team('oak', 133, "Oakland Athletics"),
        Team('phi', 143, "Philadelphia Phillies"),
        Team('pit', 134, "Pittsburgh Pirates"),
        Team('sd', 135, "San Diego Padres"),
        Team('sf', 137, "San Francisco Giants"),
        Team('sea', 136, "Seattle Mariners"),
        Team('stl', 138, "St. Louis Cardinals"),
        Team('tb', 139, "Tampa Bay Rays"),
        Team('tex', 140, "Texas Rangers"),
        Team('tor', 141, "Toronto Blue Jays"),
        Team('wsh', 120, "Washington Nationals")
    ]
    return teams_list


def increase_home_advantage(adv_score):
    return AdvantageScore(adv_score.home + 1, adv_score.away)


def increase_away_advantage(adv_score):
    return AdvantageScore(adv_score.home, adv_score.away + 1)


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
            winner.to_string()


def post_to_slack(winners):
    today = str(date.today())
    winner_str = f"{today}\n"
    for winner in winners:
        if winner.winning_team != '-':
            winner_str = winner_str + winner.get_string()
    slack.post(winner_str)


def select_winner(adv_score, game_data, odds_data):
    try:
        game_date = game_data['gameData']['datetime']['officialDate']
        if adv_score.home > adv_score.away:
            winning_team = game_data['gameData']['teams']['home']['name']
            losing_team = game_data['gameData']['teams']['away']['name']
            winning_pitcher = game_data['gameData']['probablePitchers']['home']['fullName']
            losing_pitcher = game_data['gameData']['probablePitchers']['away']['fullName']
            for result in odds_data['results']:
                if result['teams']['home']['team'] == winning_team:
                    if len(result['odds']) > 0:
                        odds = result['odds'].pop(0)['moneyline']['current']['homeOdds']
                    else:
                        odds = 0
                    return Prediction(winning_team, losing_team, winning_pitcher, losing_pitcher, game_date, odds)
            return Prediction(winning_team, losing_team, winning_pitcher, losing_pitcher, game_date, 0)
        elif adv_score.away > adv_score.home:
            winning_team = game_data['gameData']['teams']['away']['name']
            losing_team = game_data['gameData']['teams']['home']['name']
            winning_pitcher = game_data['gameData']['probablePitchers']['away']['fullName']
            losing_pitcher = game_data['gameData']['probablePitchers']['home']['fullName']
            for result in odds_data['results']:
                if result['teams']['away']['team'] == winning_team:
                    if len(result['odds']) > 0:
                        odds = result['odds'].pop(0)['moneyline']['current']['awayOdds']
                    else:
                        odds = 0
                    return Prediction(winning_team, losing_team, winning_pitcher, losing_pitcher, game_date, odds)
            return Prediction(winning_team, losing_team, winning_pitcher, losing_pitcher, game_date, 0)
        else:
            away_team = game_data['gameData']['teams']['away']['name']
            home_team = game_data['gameData']['teams']['home']['name']
            print(f"No advantage in {away_team} at {home_team} on {game_date}")
            return Prediction('-', '-', '-', '-', game_date, 0)
    except Exception as e:
        print(e)
        return Prediction('-', '-', '-', '-', game_date, 0)

