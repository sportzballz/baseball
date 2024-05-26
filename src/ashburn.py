import src.common.pickwinners as pickwinners
from src.common.util import *
import src.model.ashburn.hitting as hitting
import src.model.ashburn.pitching as pitching
import src as src


def pitching_backtest(adv_score, game_data, model):
    try:
        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']

        away_pitcher = get_pitcher_stats_by_date(away_pitcher_id, game_data['gameData']['datetime']['officialDate'])
        home_pitcher = get_pitcher_stats_by_date(home_pitcher_id, game_data['gameData']['datetime']['officialDate'])
        if len(home_pitcher['stats']) == 0 or len(away_pitcher['stats']) == 0:
            return adv_score
        elif len(home_pitcher['stats'][0]['splits']) == 0 or len(away_pitcher['stats'][0]['splits']) == 0:
            return adv_score
        else:
            home_pitcher_stats = home_pitcher['stats'][0]['splits'][0]['stat']
            away_pitcher_stats = away_pitcher['stats'][0]['splits'][0]['stat']
            return model.pitching.evaluate(adv_score, home_pitcher_stats, away_pitcher_stats)
    except Exception as e:
        d = game_data['gameData']['datetime']['officialDate']
        print(f'Unable to get Pitcher Stats: {d} {e}')


def hitting_backtest(adv_score, last_game_data, model):
    away_last_batters = get_away_batters_by_gameid(last_game_data['gamePk'])
    home_last_batters = get_home_batters_by_gameid(last_game_data['gamePk'])
    away_batting_totals = get_away_batting_total_by_game_id(last_game_data['gamePk'])
    home_batting_totals = get_home_batting_total_by_game_id(last_game_data['gamePk'])
    home_lineup_profile = get_lineup_profile_by_date(home_last_batters, last_game_data['gameData']['datetime']['officialDate'])
    away_lineup_profile = get_lineup_profile_by_date(away_last_batters, last_game_data['gameData']['datetime']['officialDate'])

    return model.hitting.evaluate(adv_score, home_batting_totals, away_batting_totals, home_lineup_profile, away_lineup_profile)


def pitching(adv_score, game_data, model):
    try:
        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']
        away_pitcher = get_pitcher_stats(away_pitcher_id)
        home_pitcher = get_pitcher_stats(home_pitcher_id)

        home_pitcher_stats = home_pitcher['stats'][0]['stats']
        away_pitcher_stats = away_pitcher['stats'][0]['stats']
    except Exception as e:
        d = game_data['gameData']['datetime']['officialDate']
        print(f'Unable to get Pitcher Stats: {d} {e}')
        return adv_score
    return src.model.ashburn.pitching.evaluate(adv_score, home_pitcher_stats, away_pitcher_stats)


def hitting(adv_score, game_data, model):
    away_team_id = game_data['gameData']['teams']['away']['id']
    home_team_id = game_data['gameData']['teams']['home']['id']
    away_last_batters = get_last_game_batters(away_team_id)
    home_last_batters = get_last_game_batters(home_team_id)
    away_batting_totals = get_last_game_batting_totals(away_team_id)
    home_batting_totals = get_last_game_batting_totals(home_team_id)
    home_lineup_profile = get_lineup_profile(home_last_batters)
    away_lineup_profile = get_lineup_profile(away_last_batters)
    return src.model.ashburn.hitting.evaluate(adv_score, home_batting_totals, away_batting_totals, home_lineup_profile, away_lineup_profile)


def main(event, context):
    print(event)
    model = "ashburn"
    pickwinners.main(model, hitting, pitching)


if __name__ == "__main__":
    main('', '')