from src.connector.stats import *
from src.common.util import *
from src.common.weights import *


def evaluate_pitching_matchup(adv_score, game_data):
    try:
        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']
        away_pitcher = get_pitcher_stats(away_pitcher_id)
        home_pitcher = get_pitcher_stats(home_pitcher_id)
        home_pitcher_stats = home_pitcher.get('stats').pop(0).get('stats')
        away_pitcher_stats = away_pitcher.get('stats').pop(0).get('stats')

        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'whip', WHIP_WEIGHT)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'winPercentage', WIN_PERCENTAGE_WEIGHT)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'strikeoutWalkRatio', STRIKEOUT_WALK_RATIO_WEIGHT)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'strikeoutsPer9Inn', STRIKEOUTS_PER_9_INN_WEIGHT)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'walksPer9Inn', WALKS_PER_9_INN_WEIGHT)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'hitsPer9Inn', HITS_PER_9_INN_WEIGHT)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'runsScoredPer9', RUNS_SCORED_PER_9_WEIGHT)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'homeRunsPer9', HOME_RUNS_PER_9_WEIGHT)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'stolenBasePercentage', STOLEN_BASE_PERCENTAGE_WEIGHT)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'groundIntoDoublePlan', GROUND_INTO_DOUBLE_PLAY_WEIGHT)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'era', ERA_WEIGHT)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'completeGames', COMPLETE_GAMES_WEIGHT)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'shutouts', SHUTOUTS_WEIGHT)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'strikePercentage', STRIKE_PERCENTAGE_WEIGHT)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'hitBatsman', HIT_BATSMAN_WEIGHT)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'balks', BALKS_WEIGHT)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'wildPitches', WILD_PITCHES_WEIGHT)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'pickoffs', PICKOFFS_WEIGHT)

    except Exception as e:
        print(e)
    return adv_score
