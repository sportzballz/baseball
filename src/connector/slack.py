import os

import pytz
from slack_sdk import WebClient
from datetime import datetime


def post_backtest(msg: str, model: str):
    client = WebClient(token=os.environ['SLACK_TOKEN'])
    client.chat_postMessage(channel=f"#{model}-backtest", text=msg, icon_emoji=':sportzballz:', username='SportzBallz')


def post_todays_pick(msg: str, model: str):
    client = WebClient(token=os.environ['SLACK_TOKEN'])
    if not is_already_posted("todays-pick"):
        client.chat_postMessage(channel=f"#todays-pick", text=msg, icon_emoji=':sportzballz:', username='SportzBallz')


def post_todays_pick_backtest(msg: str, model: str, pick_won="none"):
    client = WebClient(token=os.environ['SLACK_TOKEN'])
    # if not is_already_posted("todays-pick-backtest"):
    client.chat_postMessage(channel=f"#todays-pick-backtest", text=msg, icon_emoji=':sportzballz:', username='SportzBallz')


def post(msg: str, model: str):
    client = WebClient(token=os.environ['SLACK_TOKEN'])
    client.chat_postMessage(channel=f"#{model}-model", text=msg, icon_emoji=':sportzballz:', username='SportzBallz')
    hour = datetime.now(pytz.timezone('US/Eastern')).strftime("%H")
    # post todays-picks at 5pm
    print(f'Hour is: {hour}')
    if hour == "17":
        print(f'Posting #todays-picks')
        client.chat_postMessage(channel=f"#todays-picks", text=msg, icon_emoji=':sportzballz:', username='SportzBallz')

def post_sportzballz(msg: str):
    print(f'Posting #daily-results')
    client = WebClient(token=os.environ['SPORTZBALLZ_SLACK_TOKEN'])
    client.chat_postMessage(channel=f"#todays-picks", text=msg, icon_emoji=':sportzballz:', username='sportzballz')
    hour = datetime.now(pytz.timezone('US/Eastern')).strftime("%H")
    # post todays-picks at 5pm
    print(f'Hour is: {hour}')
    if hour == "12":
        print(f'Posting #daily-results')
        client.chat_postMessage(channel=f"#daily-results", text=msg, icon_emoji=':sportzballz:', username='SportzBallz')

def is_already_posted(target_channel: str):
    client = WebClient(token=os.environ['SLACK_TOKEN'])
    response = client.conversations_list()
    channels = response["channels"]
    already_posted = False
    for channel in channels:
        if channel["name"] == target_channel:
            id = channel["id"]
            response = client.conversations_history(channel=id)
            latest_msg = response["messages"][0]
            # print(latest_msg)
            d = datetime.fromtimestamp(int(latest_msg["ts"].split(".")[0])).strftime("%m-%d-%Y")
            today = datetime.now(pytz.timezone('US/Eastern')).strftime("%m-%d-%Y")
            if d == today:
                already_posted=True
    return already_posted

