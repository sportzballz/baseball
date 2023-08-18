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