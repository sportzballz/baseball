from src.connector.stats import *
from src.common.util import *


def evaluate_pitching_matchup(adv_score, game_data):
    try:
        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']
        away_pitcher = get_pitcher_stats(away_pitcher_id)
        home_pitcher = get_pitcher_stats(home_pitcher_id)
        home_pitcher_stats = home_pitcher.get('stats').pop(0).get('stats')
        away_pitcher_stats = away_pitcher.get('stats').pop(0).get('stats')

        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'whip', lower_is_better=True)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'winPercentage', lower_is_better=False)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'strikeoutWalkRatio', lower_is_better=True)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'strikeoutsPer9Inn', lower_is_better=False)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'walksPer9Inn', lower_is_better=True)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'hitsPer9Inn', lower_is_better=True)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'runsScoredPer9', lower_is_better=True)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'homeRunsPer9', lower_is_better=True)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'stolenBasePercentage', lower_is_better=True)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'groundIntoDoublePlan', lower_is_better=False)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'era', lower_is_better=True)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'completeGames', lower_is_better=False)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'shutouts', lower_is_better=False)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'strikePercentage', lower_is_better=False)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'hitBatsman', lower_is_better=True)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'balks', lower_is_better=True)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'wildPitches', lower_is_better=True)
        adv_score = evaluate_stat(adv_score, home_pitcher_stats, away_pitcher_stats, 'pickoffs', lower_is_better=False)

    except Exception as e:
        print(e)
    return adv_score
