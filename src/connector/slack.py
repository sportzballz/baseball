import os
from slack_sdk import WebClient


def post_backtest(msg: str):
    client = WebClient(token=os.environ['SLACK_USER_TOKEN'])
    client.chat_postMessage(channel="#sportzballz-backtest", text=msg, icon_emoji=':sportzballz:', username='SportzBallz')


def post(msg: str):
    client = WebClient(token=os.environ['SLACK_USER_TOKEN'])
    client.chat_postMessage(channel="#sportzballz", text=msg, icon_emoji=':baseball:', username='SportzBallz')

