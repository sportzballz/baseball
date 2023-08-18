from src.common.util import *


def get_whip(team):
    try:
        return float(team.get('whip'))
    except Exception:
        return 0.0


def evaluate_whip(adv_score, home_stats, away_stats):
    home_whip = get_whip(home_stats)
    away_whip = get_whip(away_stats)
    if home_whip < away_whip:
        return increase_home_advantage(adv_score)
    elif away_whip < home_whip:
        return increase_away_advantage(adv_score)
    else:
        return adv_score