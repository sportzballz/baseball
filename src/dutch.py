import src.common.pickwinners as pickwinners
from src.common.util import *
import src.model.dutch.hitting as hitting
import src.model.dutch.pitching as pitching
import src.model.dutch.vs as vs
import src as src
from datetime import datetime, timedelta


def pitching_backtest(adv_score, game_data, year):
    try:
        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']
        game_date = game_data['gameData']['datetime']['officialDate']
        yesterday = (datetime.strptime(game_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        away_pitcher = get_pitcher_stats_by_date(away_pitcher_id, yesterday)
        home_pitcher = get_pitcher_stats_by_date(home_pitcher_id, yesterday)

        away_pitcher1 = get_pitcher_stats(away_pitcher_id)
        home_pitcher1 = get_pitcher_stats(home_pitcher_id)
        if len(home_pitcher['stats']) == 0 or len(away_pitcher['stats']) == 0:
            # print("No pitcher stats found for yesterday. Skipping...")
            return adv_score
        elif len(home_pitcher['stats'][0]['splits']) == 0 or len(away_pitcher['stats'][0]['splits']) == 0:
            # print("No pitcher splits found for yesterday. Skipping...")
            return adv_score
        else:
            home_splits_count = len(home_pitcher['stats'][0]['splits'])
            away_splits_count = len(away_pitcher['stats'][0]['splits'])
            home_pitcher_stats = home_pitcher['stats'][0]['splits'][home_splits_count - 1]['stat']
            away_pitcher_stats = away_pitcher['stats'][0]['splits'][away_splits_count - 1]['stat']
            return src.model.dutch.pitching.evaluate(adv_score, home_pitcher_stats, away_pitcher_stats, test=True)
    except Exception as e:
        d = game_data['gameData']['datetime']['officialDate']
        print(f'Unable to get Pitcher Stats: {d} {e}')
        return adv_score


def hitting_backtest(adv_score, game_data, dt):
    try:
        d = datetime.strptime(dt, "%Y-%m-%d").date()
        yesterday = (datetime.strptime(dt, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        home_last_game_id = get_last_game_by_date(game_data['gameData']['teams']['home']['id'], d)
        away_last_game_id = get_last_game_by_date(game_data['gameData']['teams']['away']['id'], d)
        home_last_game_data = get_game(home_last_game_id)
        away_last_game_data = get_game(away_last_game_id)
        # away_batters = away_last_game_data["awayBatters"]
        # home_batters = home_last_game_data["homeBatters"]
        home_batters = get_home_batters_by_gameid(game_data['gamePk'])
        away_batters = get_away_batters_by_gameid(game_data['gamePk'])

        away_batting_totals = get_away_batting_total_by_game_id(away_last_game_id)
        home_batting_totals = get_home_batting_total_by_game_id(home_last_game_id)

        home_lineup_profile = get_lineup_profile_by_date(home_batters, yesterday)
        away_lineup_profile = get_lineup_profile_by_date(away_batters, yesterday)

        # away_lineup_profile1 = get_lineup_profile(away_batters)
        # home_lineup_profile1 = get_lineup_profile(home_batters)

        return src.model.dutch.hitting.evaluate(adv_score, home_batting_totals, away_batting_totals, home_lineup_profile, away_lineup_profile, test=True)
    except Exception as e:
        d = game_data['gameData']['datetime']['officialDate']
        print(f'Unable to get Hitting Stats: {d} {e}')
        return adv_score


def vs_backtest(adv_score, game_data, dt):
    try:
        away_team_id = game_data['gameData']['teams']['away']['id']
        home_team_id = game_data['gameData']['teams']['home']['id']
    # away_last_batters = get_last_game_batters(away_team_id)
    # home_last_batters = get_last_game_batters(home_team_id)
    # away_batting_totals = get_last_game_batting_totals(away_team_id)
    # home_batting_totals = get_last_game_batting_totals(home_team_id)
    # home_lineup_profile = get_lineup_profile(home_last_batters)
    # away_lineup_profile = get_lineup_profile(away_last_batters)

        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']

        return src.model.dutch.vs.evaluate(adv_score, home_pitcher_id, away_pitcher_id, home_team_id, away_team_id, dt)
    except Exception as e:
        print(f'Unable to get VS Stats: {e}')
        return adv_score


def pitching(adv_score, game_data, model, lineups):
    try:
        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        away_pitcher_full_name = game_data['gameData']['probablePitchers']['away']['fullName'].split()
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']
        away_pitcher = get_pitcher_stats(away_pitcher_id)
        home_pitcher = get_pitcher_stats(home_pitcher_id)

        home_pitcher_stats = home_pitcher['stats'][0]['stats']
        away_pitcher_stats = away_pitcher['stats'][0]['stats']
        # s = pybaseball_statcast("2019-06-24", "2019-06-25")
        # chadwick = chadwick_register()
        # player = playerid_lookup(away_pitcher_full_name[1], away_pitcher_full_name[0])
        #
        # # # print(chadwick['key_mlbam'])
        # # for mlbam in chadwick['key_mlbam']:
        # #     if mlbam['key_mlbam'] == away_pitcher_id:
        # #         print(mlbam['key_fangraphs'])
        # #         fan_id = mlbam['key_fangraphs']
        # pid = player['key_fangraphs'].values[0]
        # data = pitching_stats(2024, players=pid)
        # print(data['Stuff+'])
    except Exception as e:
        d = game_data['gameData']['datetime']['officialDate']
        print(f'Unable to get Pitcher Stats: {d} {e}')
        return adv_score
    return src.model.dutch.pitching.evaluate(adv_score, home_pitcher_stats, away_pitcher_stats)


def hitting(adv_score, game_data, model, lineups):
    away_team_id = game_data['gameData']['teams']['away']['id']
    home_team_id = game_data['gameData']['teams']['home']['id']

    for lineup in lineups:
        if lineup.team_id == away_team_id:
            away_lineup = lineup.lineup_players
        elif lineup.team_id == home_team_id:
            home_lineup = lineup.lineup_players

    away_last_batters = get_last_game_batters(away_team_id)
    home_last_batters = get_last_game_batters(home_team_id)
    away_batting_totals = get_last_game_batting_totals(away_team_id)
    home_batting_totals = get_last_game_batting_totals(home_team_id)
    if len(home_lineup) > 0:
        adv_score.home_lineup_available = True
        home_lineup_profile = get_todays_starting_lineup_profile(home_lineup)
        print(f'home lineup avalable: {adv_score.to_string()}')
    else:
        home_lineup_profile = get_lineup_profile(home_last_batters)
    if len(away_lineup) > 0:
        adv_score.away_lineup_available = True
        away_lineup_profile = get_todays_starting_lineup_profile(away_lineup)
        print(f'away lineup avalable: {adv_score.to_string()}')
    else:
        away_lineup_profile = get_lineup_profile(away_last_batters)

    return src.model.dutch.hitting.evaluate(adv_score, home_batting_totals, away_batting_totals, home_lineup_profile, away_lineup_profile)


def vs(adv_score, game_data, model, lineups):
    try:
        away_team_id = game_data['gameData']['teams']['away']['id']
        home_team_id = game_data['gameData']['teams']['home']['id']
        # away_last_batters = get_last_game_batters(away_team_id)
        # home_last_batters = get_last_game_batters(home_team_id)
        # away_batting_totals = get_last_game_batting_totals(away_team_id)
        # home_batting_totals = get_last_game_batting_totals(home_team_id)
        # home_lineup_profile = get_lineup_profile(home_last_batters)
        # away_lineup_profile = get_lineup_profile(away_last_batters)

        away_pitcher_id = game_data['gameData']['probablePitchers']['away']['id']
        home_pitcher_id = game_data['gameData']['probablePitchers']['home']['id']

        return src.model.dutch.vs.evaluate(adv_score, home_pitcher_id, away_pitcher_id, home_team_id, away_team_id, date.today())
    except Exception as e:
        d = game_data['gameData']['datetime']['officialDate']
        print(f'Unable to get Pitcher Vs Stats: {d} {e}')
        return adv_score


def main(event, context):
    print(event)
    model = "dutch"
    pickwinners.main(model, hitting, pitching, vs)


if __name__ == "__main__":
    main('', '')