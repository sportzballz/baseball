from src.common.util import *
from src.common.weights import *
from src.connector.stats import *


def evaluate_hitting_matchup_backtest(adv_score, last_game_data):
    away_last_batters = get_away_batters_by_gameid(last_game_data['gamePk'])
    home_last_batters = get_home_batters_by_gameid(last_game_data['gamePk'])
    away_batting_totals = get_away_batting_total_by_game_id(last_game_data['gamePk'])
    home_batting_totals = get_home_batting_total_by_game_id(last_game_data['gamePk'])
    home_lineup_profile = get_lineup_profile_by_date(home_last_batters, last_game_data['gameData']['datetime']['officialDate'])
    away_lineup_profile = get_lineup_profile_by_date(away_last_batters, last_game_data['gameData']['datetime']['officialDate'])

    return evaluate(adv_score, home_batting_totals, away_batting_totals, home_lineup_profile, away_lineup_profile)


def evaluate_hitting_matchup(adv_score, game_data, test=False):
    away_team_id = game_data['gameData']['teams']['away']['id']
    home_team_id = game_data['gameData']['teams']['home']['id']
    away_last_batters = get_last_game_batters(away_team_id)
    home_last_batters = get_last_game_batters(home_team_id)
    away_batting_totals = get_last_game_batting_totals(away_team_id)
    home_batting_totals = get_last_game_batting_totals(home_team_id)
    home_lineup_profile = get_lineup_profile(home_last_batters)
    away_lineup_profile = get_lineup_profile(away_last_batters)
    return evaluate(adv_score, home_batting_totals, away_batting_totals, home_lineup_profile, away_lineup_profile)


def evaluate(adv_score, home_batting_totals, away_batting_totals, home_lineup_profile, away_lineup_profile):
    adv_score = evaluate_stat(adv_score, home_batting_totals, away_batting_totals, 'r', R_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_batting_totals, away_batting_totals, 'h', H_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_batting_totals, away_batting_totals, 'hr', HR_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_batting_totals, away_batting_totals, 'rbi', RBI_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_batting_totals, away_batting_totals, 'bb', BB_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_batting_totals, away_batting_totals, 'k', K_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_batting_totals, away_batting_totals, 'lob', LOB_WEIGHT)

    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'avg', 'atBats', False)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'groundOuts', 'atBats', True)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'airOuts', 'atBats', True)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'runs', 'atBats', False)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'doubles', 'atBats', False)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'triples', 'atBats', False)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'homeRuns', 'atBats', False)
    adv_score = evaluate_player_weighted_stat(adv_score, home_lineup_profile, away_lineup_profile, 'rbi', 'atBats', False)
    return adv_score
