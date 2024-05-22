from src.connector.stats import *
from src.common.util import *
from src.common.weights import *


def evaluate_pitching_matchup_backtest(adv_score, game_data):
    away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
    home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']

    away_pitcher = get_pitcher_stats_by_date(away_pitcher_id, game_data['gameData']['datetime']['officialDate'])
    home_pitcher = get_pitcher_stats_by_date(home_pitcher_id, game_data['gameData']['datetime']['officialDate'])
    try:
        if len(home_pitcher['stats']) == 0 or len(away_pitcher['stats']) == 0:
            return adv_score
        elif len(home_pitcher['stats'][0]['splits']) == 0 or len(away_pitcher['stats'][0]['splits']) == 0:
            return adv_score
        else:
            home_pitcher_stats = home_pitcher['stats'][0]['splits'][0]['stat']
            away_pitcher_stats = away_pitcher['stats'][0]['splits'][0]['stat']
            return evaluate(adv_score, home_pitcher_stats, away_pitcher_stats)
    except Exception as e:
        d = game_data['gameData']['datetime']['officialDate']
        print(f'Unable to get Pitcher Stats: {d} {e}')


def evaluate_pitching_matchup(adv_score, game_data):
    away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
    home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']

    away_pitcher = get_pitcher_stats(away_pitcher_id)
    home_pitcher = get_pitcher_stats(home_pitcher_id)

    home_pitcher_stats = home_pitcher['stats'][0]['stats']
    away_pitcher_stats = away_pitcher['stats'][0]['stats']

    return evaluate(adv_score, home_pitcher_stats, away_pitcher_stats)


def evaluate(adv_score, home_pitcher_stats, away_pitcher_stats):
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'whip', WHIP_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'winPercentage', WIN_PERCENTAGE_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'strikeoutWalkRatio', STRIKEOUT_WALK_RATIO_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'strikeoutsPer9Inn', STRIKEOUTS_PER_9_INN_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'walksPer9Inn', WALKS_PER_9_INN_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'hitsPer9Inn', HITS_PER_9_INN_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'runsScoredPer9', RUNS_SCORED_PER_9_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'homeRunsPer9', HOME_RUNS_PER_9_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'stolenBasePercentage', STOLEN_BASE_PERCENTAGE_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'groundIntoDoublePlay', GROUND_INTO_DOUBLE_PLAY_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'era', ERA_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'completeGames', COMPLETE_GAMES_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'shutouts', SHUTOUTS_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'strikePercentage', STRIKE_PERCENTAGE_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'hitBatsmen', HIT_BATSMAN_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'balks', BALKS_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'wildPitches', WILD_PITCHES_WEIGHT)
    adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'pickoffs', PICKOFFS_WEIGHT)

    return adv_score


