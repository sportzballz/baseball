import os

from slack_sdk import WebClient

from slack_sdk.errors import SlackApiError


def post(msg: str):
    client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

    client.chat_postMessage(channel="#sportzballz", text=msg)

