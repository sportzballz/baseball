from src.common.util import *
from src.common.weights import *
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

    adv_score = evaluate_stat(adv_score, home_last_batting_totals, away_last_batting_totals, 'r', R_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_last_batting_totals, away_last_batting_totals, 'h', H_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_last_batting_totals, away_last_batting_totals, 'hr', HR_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_last_batting_totals, away_last_batting_totals, 'rbi', RBI_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_last_batting_totals, away_last_batting_totals, 'bb', BB_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_last_batting_totals, away_last_batting_totals, 'k', K_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_last_batting_totals, away_last_batting_totals, 'lob', LOB_WEIGHT)

    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'avg', 'atBats', lower_is_better=False)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'groundOuts', 'atBats', lower_is_better=True)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'airOuts', 'atBats', lower_is_better=True)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'runs', 'atBats', lower_is_better=False)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'doubles', 'atBats', lower_is_better=False)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'triples', 'atBats', lower_is_better=False)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'homeRuns', 'atBats', lower_is_better=False)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'rbi', 'atBats', lower_is_better=False)
    return adv_score
