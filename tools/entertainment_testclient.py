#!/usr/bin/env python3
"""Entertainment test client.

Drives an entertainment area of a bridge the way a Hue Sync Box does:
activates the stream over the REST API, opens a DTLS-PSK connection to
port 2100 and writes HueStream v2 frames with random colours. Useful to
check the streaming path without physical sync hardware.

Example:

    tools/entertainment_testclient.py \
        --host 192.168.1.20 --user <application-key> \
        --psk <entertainment-client-key> --group 1 --frames 40

The application key identifies the API user, the client key is the
entertainment credential (hex or base64url).
"""
import argparse
import base64
import binascii
import json
import random
import subprocess
import sys
import time
import urllib.error
import urllib.request

MAGIC = b"HueStream"
API_VERSION = (0x02, 0x00)      # HueStream 2.0
COLOUR_SPACE_RGB = 0x00
COLOUR_SPACE_XY = 0x01
DEFAULT_CIPHERS = "PSK-AES128-CBC-SHA:PSK-AES128-GCM-SHA256:@SECLEVEL=0"


def call(host, path, method="GET", body=None, user=None, timeout=10):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(f"http://{host}{path}", data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if user:
        request.add_header("hue-application-key", user)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        raise SystemExit(f"{method} {path} failed: {error.code} {error.read()[:200]!r}")


def psk_hex(clientkey):
    """Return the PSK as hex digits, the form openssl expects."""
    if all(c in "0123456789abcdefABCDEF" for c in clientkey) and len(clientkey) % 2 == 0:
        return clientkey
    decoded = base64.urlsafe_b64decode(clientkey + "=" * (-len(clientkey) % 4))
    return binascii.hexlify(decoded).decode()


def area_channels(host, user, group):
    """Return (area id, channel ids) for a group, else the first usable area."""
    areas = call(host, "/clip/v2/resource/entertainment_configuration",
                 user=user).get("data", [])
    area = next((a for a in areas if a.get("id_v1") == f"/groups/{group}"), None)
    if area is None:
        area = next((a for a in areas if a.get("channels")), None)
    if area is None:
        return None, []
    return area["id"], [channel["channel_id"] for channel in area.get("channels", [])]


def build_frame(sequence, area_id, channels, colours, colour_space=COLOUR_SPACE_RGB):
    """Build one HueStream v2 frame.

    Layout: magic, version, sequence, two reserved bytes, colour space, one
    reserved byte, the area id padded to 36 ASCII bytes, then seven bytes per
    channel: channel id followed by three 16 bit big endian values.
    """
    payload = bytearray(MAGIC)
    payload += bytes(API_VERSION)
    payload += bytes([sequence & 0xFF])
    payload += b"\x00\x00"
    payload += bytes([colour_space])
    payload += b"\x00"
    payload += area_id.encode()[:36].ljust(36, b"\x00")
    for channel in channels:
        values = colours.get(channel) or (0, 0, 0)
        payload += bytes([channel & 0xFF])
        for value in values:
            value = max(0, min(0xFFFF, int(value)))
            payload += bytes([(value >> 8) & 0xFF, value & 0xFF])
    return bytes(payload)


def open_dtls(host, psk, identity, cipher, port=2100, wait=2.0):
    command = ["openssl", "s_client", "-dtls1_2", "-quiet", "-cipher", cipher,
               "-psk", psk, "-psk_identity", identity, "-connect", f"{host}:{port}"]
    process = subprocess.Popen(command, stdin=subprocess.PIPE,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    time.sleep(wait)
    if process.poll() is not None:
        raise SystemExit("DTLS handshake failed: " +
                         process.stderr.read().decode(errors="replace").strip())
    return process


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", required=True, help="bridge address")
    parser.add_argument("--user", required=True, help="application key (API user)")
    parser.add_argument("--psk", required=True, help="entertainment client key (hex or base64url)")
    parser.add_argument("--identity", default=None, help="PSK identity (default: the user)")
    parser.add_argument("--group", default="1", help="group whose stream is used")
    parser.add_argument("--cipher", default=DEFAULT_CIPHERS, help="openssl cipher list")
    parser.add_argument("--frames", type=int, default=40, help="number of frames")
    parser.add_argument("--delay", type=float, default=0.25, help="seconds between frames")
    parser.add_argument("--on", action="store_true",
                        help="switch the lamps of the area on before streaming")
    parser.add_argument("--off", action="store_true",
                        help="switch the lamps of the area off when the stream ends")
    args = parser.parse_args()

    identity = args.identity or args.user
    area_id, channels = area_channels(args.host, args.user, args.group)
    if not area_id:
        raise SystemExit("no entertainment area with channels on this bridge")
    print(f"area {area_id}, channels {channels}")

    # The bridge marks the lamps as on when the stream starts, but it does not
    # switch them on: a lamp that was off stays dark while colours arrive.
    call(args.host, f"/api/{args.user}/groups/{args.group}/action", "PUT",
         {"on": True, "bri": 254})
    if args.on:
        call(args.host, f"/api/{args.user}/groups/{args.group}/action", "PUT",
             {"on": True, "bri": 254})
        time.sleep(0.5)
    call(args.host, f"/api/{args.user}/groups/{args.group}", "PUT",
         {"stream": {"active": True}})
    time.sleep(1.0)
    process = open_dtls(args.host, psk_hex(args.psk), identity, args.cipher)
    print(f"DTLS up, sending {args.frames} frames")
    try:
        for sequence in range(args.frames):
            colours = {channel: (random.randint(0, 0xFFFF), random.randint(0, 0xFFFF),
                                 random.randint(0, 0xFFFF)) for channel in channels}
            process.stdin.write(build_frame(sequence, area_id, channels, colours))
            process.stdin.flush()
            time.sleep(args.delay)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            process.stdin.close()
        except Exception:
            pass
        process.terminate()
        call(args.host, f"/api/{args.user}/groups/{args.group}", "PUT",
             {"stream": {"active": False}})
        if args.off:
            time.sleep(1)
            call(args.host, f"/api/{args.user}/groups/{args.group}/action", "PUT",
                 {"on": False})
            print("lamps switched off")
        print("stream stopped")


if __name__ == "__main__":
    sys.exit(main())
