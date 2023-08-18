from src.common.util import *


def get_win_pct(team):
    try:
        return float(team.get('winPercentage'))
    except Exception:
        return 0.0


def evaluate_pitcher_win_percentage(adv_score, home_stats, away_stats):
    home_win_pct = get_win_pct(home_stats)
    away_win_pct = get_win_pct(away_stats)
    if home_win_pct > away_win_pct:
        return increase_home_advantage(adv_score)
    elif away_win_pct > home_win_pct:
        return increase_away_advantage(adv_score)
    else:
        return adv_score
