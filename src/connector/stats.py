import statsapi
from datetime import date


def get_pitcher_stats(player_id):
    return statsapi.player_stat_data(personId=player_id, group='pitching')


def get_todays_game(team_id):
    return statsapi.schedule(date=date.today(), team=team_id)