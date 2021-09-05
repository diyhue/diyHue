import configManager
import logManager
from flask import Flask, Response, stream_with_context, Blueprint
import json
from time import sleep, time

logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.yaml_config
stream = Blueprint('stream',__name__)

messages = []

def messageBroker():
    global messages
    while True:
        if len(bridgeConfig["temp"]["eventstream"]) > 0:
            for event in bridgeConfig["temp"]["eventstream"]:
                messages.append(event)
                logging.debug(event)
            bridgeConfig["temp"]["eventstream"] = []
            sleep(0.6) # ensure all devices connected receive the events
            messages = []
        sleep(0.5)


@stream.route('/eventstream/clip/v2')
def streamV2Events():
    def generate():
        counter = 1000
        yield f": hi\n\n"
        while counter > 0: # ensure we stop at some point
            if len(messages) > 0:
                yield f"id: {int(time()) }:0\ndata: {json.dumps(messages)}\n\n"
            sleep(0.5)
            counter -=1

    return Response(stream_with_context(generate()), mimetype='text/event-stream; charset=utf-8')
