from src.common.util import *
from src.connector.stats import *


def evaluate_hitting_matchup_backtest(adv_score, last_game_data, model):
    away_last_batters = get_away_batters_by_gameid(last_game_data['gamePk'])
    home_last_batters = get_home_batters_by_gameid(last_game_data['gamePk'])
    away_batting_totals = get_away_batting_total_by_game_id(last_game_data['gamePk'])
    home_batting_totals = get_home_batting_total_by_game_id(last_game_data['gamePk'])
    home_lineup_profile = get_lineup_profile_by_date(home_last_batters, last_game_data['gameData']['datetime']['officialDate'])
    away_lineup_profile = get_lineup_profile_by_date(away_last_batters, last_game_data['gameData']['datetime']['officialDate'])

    return model.hitting.evaluate(adv_score, home_batting_totals, away_batting_totals, home_lineup_profile, away_lineup_profile)


def evaluate_hitting_matchup(adv_score, game_data, model):
    away_team_id = game_data['gameData']['teams']['away']['id']
    home_team_id = game_data['gameData']['teams']['home']['id']
    away_last_batters = get_last_game_batters(away_team_id)
    home_last_batters = get_last_game_batters(home_team_id)
    away_batting_totals = get_last_game_batting_totals(away_team_id)
    home_batting_totals = get_last_game_batting_totals(home_team_id)
    home_lineup_profile = get_lineup_profile(home_last_batters)
    away_lineup_profile = get_lineup_profile(away_last_batters)
    return model.hitting.evaluate(adv_score, home_batting_totals, away_batting_totals, home_lineup_profile, away_lineup_profile)



