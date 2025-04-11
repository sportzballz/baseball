import os
import http
import json
from datetime import date, datetime

import pytz


def get_odds():
    conn = http.client.HTTPSConnection("sportspage-feeds.p.rapidapi.com")
    key = os.environ["SPORTSPAGE_API_KEY"]
    headers = {
        'X-RapidAPI-Key': key,
        'X-RapidAPI-Host': "sportspage-feeds.p.rapidapi.com"
    }
    today = str(datetime.now(pytz.timezone('US/Eastern')).date())
    conn.request("GET", "/games?odds=moneyline&status=scheduled&league=MLB&date=" + today, headers=headers)

    res = conn.getresponse()
    data = res.read()
    dataStr = data.decode("utf-8").replace("'", '"')
    dataList = json.loads(dataStr)

    return dataList
