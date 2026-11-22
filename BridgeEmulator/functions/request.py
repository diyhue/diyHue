import requests
from time import sleep

def localBaseUrl():
    """http://host:port of this bridge, honouring --http-port and --bind-ip."""
    import configManager
    args = getattr(getattr(configManager, "runtimeConfig", None), "arg", {}) or {}
    host = args.get("BIND_IP") or "127.0.0.1"
    if host in ("0.0.0.0", "::"):
        host = "127.0.0.1"
    if ":" in host:
        host = "[" + host + "]"
    return "http://" + host + ":" + str(args.get("HTTP_PORT") or 80)


def sendRequest(url, method, data, timeout=3, delay=0):
    if delay != 0:
        sleep(delay)
    if not url.startswith( 'http' ):
        url = localBaseUrl() + url
    head = {"Content-type": "application/json"}
    if method == "POST":
        if type(data) is dict:
            response = requests.post(url, data=data, timeout=timeout)
        else:
            response = requests.post(url, data=bytes(data, "utf8"), timeout=timeout, headers=head)
        return response.text
    elif method == "PUT":
        response = requests.put(url, data=bytes(data, "utf8"), timeout=timeout, headers=head)
        return response.text
    elif method == "GET":
        response = requests.get(url, timeout=timeout, headers=head)
        return response.text
