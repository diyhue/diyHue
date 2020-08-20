import json

def load_config(path):
    with open(path, 'r', encoding="utf-8") as fp:
        return json.load(fp)

def init():
    global bridgeConfig
    bridgeConfig = {}
    bridgeConfig = load_config('config.json')
