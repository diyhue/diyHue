import logManager
from flask import Response, stream_with_context, Blueprint
import json
from time import sleep, time
import HueObjects

logging = logManager.logger.get_logger(__name__)
stream = Blueprint('stream', __name__)

def messageBroker():
    # Events are retained in a bounded sequence history.
    # Do not clear them globally because connected clients may
    # not have consumed them yet.
    while True:
        sleep(60)

@stream.route('/eventstream/clip/v2')
def streamV2Events():
    def generate():
        # Each client tracks its own position in the event history.
        last_seq = HueObjects.EventStreamSequence()
        last_heartbeat = time()

        yield ": hi\n\n"

        while True:
            events = HueObjects.EventStreamSnapshot(last_seq)

            for seq, messages in events:
                if isinstance(messages, list):
                    payload = messages
                else:
                    payload = [messages]

                yield (
                    f"id: {seq}\n"
                    f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"
                )

                last_seq = seq

            if time() - last_heartbeat >= 15:
                yield ": keepalive\n\n"
                last_heartbeat = time()

            sleep(0.1)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream; charset=utf-8'
    )
