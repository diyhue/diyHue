"""Remote API client for Hue Essentials "Away from home".

The bridge long-polls remote.diyhue.org for requests queued by the app,
executes them against the local API and posts the result back.

Protocol v2 (``&v=2``): each action carries an ``id``, the HTTP method
(GET/POST/PUT/DELETE), the bridge path (``api/...`` for Hue API v1 or
``clip/v2/...`` for Hue API v2) and the ``hue-application-key`` header.  The
answer is an envelope ``{"id", "status", "contentType", "body"}`` so status
codes and v2 error bodies reach the app unchanged.  Actions are executed in
their own thread, so several app requests can be served at the same time.

Actions without an ``id`` come from an older relay server; for those the
local response is posted back as plain JSON, like before.
"""
import base64
import json
import re
from threading import Thread
from time import sleep

import requests

import logManager

logging = logManager.logger.get_logger(__name__)

REMOTE_URL = 'https://remote.diyhue.org/devices'
PROTOCOL_VERSION = 2
POLL_TIMEOUT = 35
LOCAL_TIMEOUT = 10

ALLOWED_METHODS = ("GET", "POST", "PUT", "DELETE")
# Only the Hue APIs are reachable remotely, never the diyHue web UI / admin endpoints.
ALLOWED_ADDRESS = re.compile(r'^(api(/|\?|$)|clip/v2/|auth/v1(/|\?|$))')
# Headers from the app that are passed to the local API.
FORWARDED_HEADERS = ("hue-application-key",)


def _encoded_key(config):
    return base64.urlsafe_b64encode(bytes(config["Hue Essentials key"], "utf8")).decode("utf-8")


def _remote_params(config):
    return {"apikey": _encoded_key(config), "v": PROTOCOL_VERSION}


def _local_base(bind_ip, http_port):
    host = "127.0.0.1" if bind_ip in ("", "0.0.0.0", None) else bind_ip
    if ":" in host:
        host = f"[{host}]"
    return f"http://{host}:{http_port}"


def _error(status, description):
    return {"status": status, "contentType": "application/json",
            "body": json.dumps({"errors": [{"description": description}], "data": []})}


def execute(base_url, action):
    """Run one relayed action against the local API and return the v2 envelope (without id)."""
    method = str(action.get("method", "")).upper()
    address = str(action.get("address", "")).lstrip("/")
    if method not in ALLOWED_METHODS or not ALLOWED_ADDRESS.match(address) or ".." in address:
        logging.warning("remote API: refused %s %s", method, address)
        return _error(403, "request not allowed over the remote API")

    headers = {}
    for name, value in (action.get("headers") or {}).items():
        if name.lower() in FORWARDED_HEADERS and isinstance(value, str):
            headers[name.lower()] = value
    kwargs = {"headers": headers, "timeout": LOCAL_TIMEOUT}
    if method in ("POST", "PUT") and action.get("body") is not None:
        kwargs["json"] = action["body"]

    try:
        response = requests.request(method, f"{base_url}/{address}", **kwargs)
    except requests.RequestException as e:
        logging.debug("remote API: local request failed: %s", e)
        return _error(502, "bridge did not answer")
    return {"status": response.status_code,
            "contentType": response.headers.get("Content-Type", "application/json"),
            "body": response.text}


def handle_action(base_url, config, action):
    result = execute(base_url, action)
    if action.get("id"):
        payload = dict(result, id=action["id"])
    else:
        # older relay server: it expects the bare JSON response
        try:
            payload = json.loads(result["body"])
        except ValueError:
            payload = json.loads(_error(502, "bridge returned invalid json")["body"])
    try:
        requests.post(REMOTE_URL, params=_remote_params(config), json=payload, timeout=LOCAL_TIMEOUT)
    except requests.RequestException as e:
        logging.debug("remote API: could not send response: %s", e)


def runRemoteApi(BIND_IP, config, HTTP_PORT=80):
    base_url = _local_base(BIND_IP, HTTP_PORT)
    session = requests.Session()
    while True:
        if not config["Remote API enabled"]:
            sleep(10)  # sleep if remote access is not enabled
            continue
        try:
            response = session.get(REMOTE_URL, params=_remote_params(config), timeout=POLL_TIMEOUT)
        except requests.RequestException:
            logging.debug("remote server is down")
            sleep(60)  # don't overload the remote server
            continue
        except Exception:
            logging.exception("remote API poll failed")
            sleep(60)
            continue

        if response.status_code != 200:
            logging.debug("remote server error: %s, %s", response.status_code, response.text)
            sleep(30)  # don't overload the remote server
            continue
        if response.text.strip() == "{renew}":
            continue
        try:
            action = response.json()
        except ValueError:
            logging.debug("remote server sent invalid data")
            sleep(1)
            continue
        if isinstance(action, dict):
            Thread(target=handle_action, args=(base_url, config, action), daemon=True).start()
