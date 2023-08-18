from src.connector.stats import *
from src.analysis.pitching.conditions.whip import evaluate_whip
from src.analysis.pitching.conditions.winpercentage import evaluate_pitcher_win_percentage


def evaluate_pitching_matchup(adv_score, game_data):
    try:
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
