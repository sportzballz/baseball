import statsapi
from datetime import date


def get_pitcher_stats(player_id):
    return statsapi.player_stat_data(personId=player_id, group='pitching')


def get_todays_games(team_id):
    return statsapi.schedule(date=date.today(), team=team_id)


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