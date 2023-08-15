import statsapi
import json


def main():
    # data = statsapi.schedule(start_date='08/15/2023',end_date='08/15/2023')
    data = statsapi.lookup_team('chi')
    # statsapi.meta(type, fields=None)

    print(json.dumps(data, indent=2))
