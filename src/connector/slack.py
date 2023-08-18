import os
from slack_sdk import WebClient


def post(msg: str):
    client = WebClient(token=os.environ['SLACK_TOKEN'])
    client.chat_postMessage(channel="#sportzballz", text=msg, icon_emoji=':baseball:', username='SportzBallz')

