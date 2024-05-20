from src.common.util import *
from src.connector.stats import *


def evaluate_hitting_matchup(adv_score, game_data):
    away_team_id = game_data['gameData']['teams']['away']['id']
    home_team_id = game_data['gameData']['teams']['home']['id']
    away_last_batters = get_last_game_batters(away_team_id)
    home_last_batters = get_last_game_batters(home_team_id)
    away_last_batting_totals = get_last_game_batting_totals(away_team_id)
    home_last_batting_totals = get_last_game_batting_totals(home_team_id)

    home_lineup_profile = get_lineup_profile(home_last_batters)
    away_lineup_profile = get_lineup_profile(away_last_batters)

    adv_score = evaluate_stat(adv_score, home_last_batting_totals, away_last_batting_totals, 'r', lower_is_better=False)
    adv_score = evaluate_stat(adv_score, home_last_batting_totals, away_last_batting_totals, 'h', lower_is_better=False)
    adv_score = evaluate_stat(adv_score, home_last_batting_totals, away_last_batting_totals, 'hr', lower_is_better=False)
    adv_score = evaluate_stat(adv_score, home_last_batting_totals, away_last_batting_totals, 'rbi', lower_is_better=False)
    adv_score = evaluate_stat(adv_score, home_last_batting_totals, away_last_batting_totals, 'bb', lower_is_better=False)
    adv_score = evaluate_stat(adv_score, home_last_batting_totals, away_last_batting_totals, 'k', lower_is_better=True)
    adv_score = evaluate_stat(adv_score, home_last_batting_totals, away_last_batting_totals, 'lob', lower_is_better=True)

    adv_score = evaluate_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'avg', lower_is_better=False)
    adv_score = evaluate_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'groundOuts', lower_is_better=True)
    adv_score = evaluate_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'airOuts', lower_is_better=True)
    adv_score = evaluate_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'runs', lower_is_better=False)
    adv_score = evaluate_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'doubles', lower_is_better=False)
    adv_score = evaluate_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'triples', lower_is_better=False)
    adv_score = evaluate_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'homeRuns', lower_is_better=False)
    adv_score = evaluate_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'rbi', lower_is_better=False)
    return adv_score
