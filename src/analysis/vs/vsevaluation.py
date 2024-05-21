from src.connector.stats import *
from src.common.util import *
from src.analysis.vs.vsutil import *


def evaluate_vs_matchup(adv_score, game_data):
    try:
        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']
        away_pitcher = get_pitcher_stats(away_pitcher_id)
        home_pitcher = get_pitcher_stats(home_pitcher_id)
        home_pitcher_stats = home_pitcher.get('stats').pop(0).get('stats')
        away_pitcher_stats = away_pitcher.get('stats').pop(0).get('stats')

        away_team_id = game_data['gameData']['teams']['away']['id']
        home_team_id = game_data['gameData']['teams']['home']['id']
        away_last_batters = get_last_game_batters(away_team_id)
        home_last_batters = get_last_game_batters(home_team_id)
        away_last_batting_totals = get_last_game_batting_totals(away_team_id)
        home_last_batting_totals = get_last_game_batting_totals(home_team_id)

        home_lineup_profile = get_lineup_profile(home_last_batters)
        away_lineup_profile = get_lineup_profile(away_last_batters)

        game_ids = get_vs_game_ids(home_team_id, away_team_id)

        adv_score = head_to_head_record(home_team_id, away_team_id, game_ids, adv_score)



        ## last 10 games record head to head
        ## Season stats Lineup against pitcher
        ## Lineup against handedness

    except Exception as e:
        print(e)
    return adv_score
