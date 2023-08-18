from src.analysis.batting.conditions.ops import evaluate_ops


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
