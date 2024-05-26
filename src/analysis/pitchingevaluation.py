from src.common.util import *
from src.analysis.model.ashburn.weights import *


def evaluate_pitching_matchup_backtest(adv_score, game_data, model):
    try:
        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']

        away_pitcher = get_pitcher_stats_by_date(away_pitcher_id, game_data['gameData']['datetime']['officialDate'])
        home_pitcher = get_pitcher_stats_by_date(home_pitcher_id, game_data['gameData']['datetime']['officialDate'])
        if len(home_pitcher['stats']) == 0 or len(away_pitcher['stats']) == 0:
            return adv_score
        elif len(home_pitcher['stats'][0]['splits']) == 0 or len(away_pitcher['stats'][0]['splits']) == 0:
            return adv_score
        else:
            home_pitcher_stats = home_pitcher['stats'][0]['splits'][0]['stat']
            away_pitcher_stats = away_pitcher['stats'][0]['splits'][0]['stat']
            return model.pitching.evaluate(adv_score, home_pitcher_stats, away_pitcher_stats)
    except Exception as e:
        d = game_data['gameData']['datetime']['officialDate']
        print(f'Unable to get Pitcher Stats: {d} {e}')


def evaluate_pitching_matchup(adv_score, game_data, model):
    try:
        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']
        away_pitcher = get_pitcher_stats(away_pitcher_id)
        home_pitcher = get_pitcher_stats(home_pitcher_id)

        home_pitcher_stats = home_pitcher['stats'][0]['stats']
        away_pitcher_stats = away_pitcher['stats'][0]['stats']
    except Exception as e:
        d = game_data['gameData']['datetime']['officialDate']
        print(f'Unable to get Pitcher Stats: {d} {e}')
        return adv_score
    return model.pitching.evaluate(adv_score, home_pitcher_stats, away_pitcher_stats)




