import json

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

VERSION = "__DEV__VERSION__"