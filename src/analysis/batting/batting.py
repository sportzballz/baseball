from src.common.util import *


def get_ops(team):
    try:
        return float(team.get('batting').get('ops'))
    except Exception:
        return 0.0


def evaluate_ops(adv_score, home, away):
    home_ops = get_ops(home)
    away_ops = get_ops(away)
    if home_ops < away_ops:
        return increase_home_advantage(adv_score)
    elif away_ops < home_ops:
        return increase_away_advantage(adv_score)
    else:
        return adv_score


def evaluate_hitting_matchup(adv_score, game_data):
    # away_lineup_ids = game_data.get('liveData').get('boxscore').get('teams').get('away').get('batters')
    home_stats = game_data.get('liveData').get('boxscore').get('teams').get('home').get('teamStats')
    # home_team_ops = home_stats.get('batting').get('ops')
    away_stats = game_data.get('liveData').get('boxscore').get('teams').get('away').get('teamStats')
    # away_team_ops = away_stats.get('batting').get('ops')
    # home_lineup_ids = game_data.get('liveData').get('boxscore').get('teams').get('home').get('batters')
    # home_team_ops = game_data.get('liveData').get('boxscore').get('teams').get('home').get('teamStats').get(
    #     'batting').get('ops')

    adv_score = evaluate_ops(adv_score, home_stats, away_stats)
    return adv_score
