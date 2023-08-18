from src.common.util import *
from src.connector.stats import *



def get_win_pct(team):
    try:
        return float(team.get('winPercentage'))
    except Exception:
        return 0.0

def get_whip(team):
    try:
        return float(team.get('whip'))
    except Exception:
        return 0.0


def evaluate_pitcher_win_percentage(adv_score, home_stats, away_stats):
    home_win_pct = get_win_pct(home_stats)
    away_win_pct = get_win_pct(away_stats)
    if home_win_pct > away_win_pct:
        return increase_home_advantage(adv_score)
    elif away_win_pct > home_win_pct:
        return increase_away_advantage(adv_score)
    else:
        return adv_score


def evaluate_whip(adv_score, home_stats, away_stats):
    home_whip = get_whip(home_stats)
    away_whip = get_whip(away_stats)
    if home_whip < away_whip:
        return increase_home_advantage(adv_score)
    elif away_whip < home_whip:
        return increase_away_advantage(adv_score)
    else:
        return adv_score


def evaluate_pitching_matchup(adv_score, game_data):
    try:
        # away_pitcher_name = game_data['gameData']['probablePitchers']['away']['fullName']
        # home_pitcher_name = game_data['gameData']['probablePitchers']['home']['fullName']
        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']
        away_pitcher_stats = get_pitcher_stats(away_pitcher_id)
        home_pitcher_stats = get_pitcher_stats(home_pitcher_id)
        home_stats = home_pitcher_stats.get('stats').pop(0).get('stats')
        away_stats = away_pitcher_stats.get('stats').pop(0).get('stats')

        adv_score = evaluate_whip(adv_score, home_stats, away_stats)
        adv_score = evaluate_pitcher_win_percentage(adv_score, home_stats, away_stats)
    except Exception as e:
        print(e)
    return adv_score
