import json

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

APP_NAME = "QualsSync"
VERSION = "__DEV__VERSION__"
