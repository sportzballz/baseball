import os
from slack_sdk import WebClient


def post_backtest(msg: str, model: str):
    client = WebClient(token=os.environ['SLACK_TOKEN'])
    client.chat_postMessage(channel=f"#{model}-backtest", text=msg, icon_emoji=':sportzballz:', username='SportzBallz')


def post(msg: str, model: str):
    client = WebClient(token=os.environ['SLACK_TOKEN'])
    client.chat_postMessage(channel=f"#{model}-model", text=msg, icon_emoji=':baseball:', username='SportzBallz')

