#!/usr/bin/env python

import argparse
import json
import logging
from typing import Dict, cast

import requests

import helpers.telegram_notify.config as htc
import helpers.telegram_notify.telegram_notify as httn

_LOG = logging.getLogger(__name__)
_LOG.setLevel(logging.INFO)


def _get_updates_dict(token: str) -> dict:
    updates_cont = requests.post(
        "https://api.telegram.org/bot{token}/getUpdates".format(token=token)
    ).content
    updates_dict = json.loads(updates_cont)
    assert updates_dict["ok"], updates_dict
    return cast(dict, updates_dict)


def _get_username_id(updates_dict: dict) -> Dict[str, str]:
    return {
        result["message"]["from"]["username"]: result["message"]["from"]["id"]
        for result in updates_dict["result"]
    }


def _get_chat_id_updates_dict(username: str, updates_dict: dict) -> str:
    username_id = _get_username_id(updates_dict)
    assert username in username_id.keys(), (
        "Either the username is wrong or you"
        " have not sent a message to the bot yet"
    )
    return username_id[username]


def send_chat_id(token: str, username: str) -> str:
    updates_dict = _get_updates_dict(token)
    chat_id = _get_chat_id_updates_dict(username, updates_dict)
    httn.TelegramNotify.send(
        text="Your chat id is: %s" % chat_id, token=token, chat_id=chat_id
    )
    return chat_id


def _main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--username", required=True, action="store", type=str)
    parser.add_argument("--token", required=False, action="store", type=str)
    args = parser.parse_args()
    username = args.username
    if args.token:
        token_ = args.token
    else:
        _LOG.info("Using default token for NotifyJupyterBot.")
        token_ = htc.NOTIFY_JUPYTER_TOKEN
    chat_id_ = send_chat_id(token_, username)
    print("Your chat id is: %s" % chat_id_)


if __name__ == "__main__":
    _main()
