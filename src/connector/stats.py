import statsapi
from datetime import date


def get_pitcher_stats(player_id):
    return statsapi.player_stat_data(personId=player_id, group='pitching')


def get_todays_games(team_id, day):
    return statsapi.schedule(date=day, team=team_id)


def get_team_data(team_id):
    return statsapi.get("team", {"teamId": team_id})


def get_last_game_batters(team_id):
    last_game_id = statsapi.last_game(team_id)
    last_boxscore = statsapi.boxscore_data(last_game_id)
    if last_boxscore['teamInfo']['home']['id'] == team_id:
        return last_boxscore['homeBatters']
    else:
        return last_boxscore['awayBatters']


def get_last_game_batting_totals(team_id):
    last_game_id = statsapi.last_game(team_id)
    last_boxscore = statsapi.boxscore_data(last_game_id)
    if last_boxscore['teamInfo']['home']['id'] == team_id:
        return last_boxscore['homeBattingTotals']
    else:
        return last_boxscore['awayBattingTotals']


def get_game(game_id):
    return statsapi.boxscore_data(game_id)


def get_vs_game_ids(home, away):
    game_id_list = []
    # year = date.today().year
    # start_date = f'04/01/{year}'
    # games = statsapi.schedule(start_date=start_date, end_date=date.today(), team=home, opponent=away)
    # for game in games:
    #     game_id_list.append(game['game_id'])
    return game_id_list

