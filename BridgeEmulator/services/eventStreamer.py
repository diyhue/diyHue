import logManager
from flask import Response, stream_with_context, Blueprint, request
import json
from time import sleep, time
import HueObjects

logging = logManager.logger.get_logger(__name__)
stream = Blueprint('stream', __name__)


def _json_default(value):
    """Serialize legacy event payloads containing Hue model objects."""
    get_v2 = getattr(value, "getV2Api", None)
    if callable(get_v2):
        return get_v2()

    object_id = getattr(value, "id_v2", None)
    if object_id is not None:
        return {
            "rid": object_id,
            "rtype": "light" if value.__class__.__name__ == "Light" else "device",
        }

    return str(value)

def messageBroker():
    # Events are retained in a bounded sequence history.
    # Do not clear them globally because connected clients may
    # not have consumed them yet.
    while True:
        sleep(60)

@stream.route('/eventstream/clip/v2')
def streamV2Events():
    def generate():
        # Resume only when the client explicitly supplies an SSE cursor.
        # Replaying an arbitrary history on a fresh connection resurrects
        # resources which were already deleted in the client's local graph.
        try:
            last_seq = int(request.headers.get("Last-Event-ID", ""))
        except (TypeError, ValueError):
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
                    f"data: {json.dumps(payload, separators=(',', ':'), default=_json_default)}\n\n"
                )

                last_seq = seq

            if time() - last_heartbeat >= 15:
                yield ": keepalive\n\n"
                last_heartbeat = time()

            sleep(0.1)

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )
