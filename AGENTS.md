# AGENTS.md

## Project overview

diyHue is a Philips Hue Bridge emulator written in Python (Flask). It bridges smart lights, sensors, and switches from many ecosystems (Zigbee, Yeelight, WLED, Tasmota, Home Assistant, etc.) into a unified Hue-compatible API.

- **App repo**: https://github.com/diyhue/diyHue
- **Docs repo**: https://github.com/diyhue/ReadTheDocs
- **Docs site**: https://diyhue.readthedocs.io/

Docker is the **only officially supported** install method. Manual/host install is Linux-only and community-maintained. macOS is not officially supported but works for development (see caveats below).

## Setup (macOS)

```bash
# Create and activate virtual environment (one-time)
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

The `.venv/` directory is git-ignored. Always activate it before running the app or installing packages.

### Install the web UI

The frontend is a **separate project** ([diyhue/diyHueUI](https://github.com/diyhue/diyHueUI)) and is NOT included in the repo clone. The Dockerfile and `install.sh` both download it at build time. On macOS, install it manually:

```bash
curl -sL https://github.com/diyhue/diyHueUI/releases/latest/download/DiyHueUI-release.zip -o /tmp/diyHueUI.zip
unzip -qo /tmp/diyHueUI.zip -d /tmp/diyhueUI
mv /tmp/diyhueUI/dist/index.html BridgeEmulator/flaskUI/templates/
cp -r /tmp/diyhueUI/dist/assets BridgeEmulator/flaskUI/
rm -r /tmp/diyhueUI /tmp/diyHueUI.zip
```

### Fix missing layout templates

The repo is also missing two Jinja layout templates referenced by the error pages and devices page. These must be created manually:

```bash
mkdir -p BridgeEmulator/flaskUI/templates/layouts
```

Create `BridgeEmulator/flaskUI/templates/layouts/base-error.html` and `BridgeEmulator/flaskUI/templates/layouts/base.html` — see those files in the repo for the current content.

### Optional dev tools

```bash
brew install nmap         # light autodiscovery
brew install libcoap      # CoAP protocol (coap-client)
brew install libfaketime  # backdate certificates (needed for official Hue app)
```

## Certificate (required — do this before first launch)

The app requires a certificate even with HTTPS disabled. The certificate serial must use **EUI-64 format** (`<MAC first 6 hex>fffe<MAC last 6 hex>`) and be generated with the project's `openssl.conf`. Use your **real network MAC address** — the official Hue app verifies the cert against the interface MAC.

```bash
# Get your real MAC
REAL_MAC=$(ifconfig en0 | grep ether | awk '{print $2}')
MAC_CLEAN="${REAL_MAC//:/}"
# EUI-64 serial: first 6 chars + fffe + last 6 chars
SERIAL_HEX="${MAC_CLEAN:0:6}fffe${MAC_CLEAN:6:6}"
DEC_SERIAL=$(python3 -c "print(int('$SERIAL_HEX', 16))")

# Generate cert using project's openssl.conf
openssl req -new -days 7670 \
  -config BridgeEmulator/openssl.conf \
  -nodes -x509 -newkey ec \
  -pkeyopt ec_paramgen_curve:P-256 \
  -pkeyopt ec_param_enc:named_curve \
  -subj "/C=NL/O=Philips Hue/CN=$SERIAL_HEX" \
  -keyout config/private.key \
  -out config/public.crt \
  -set_serial $DEC_SERIAL

cat config/private.key > config/cert.pem
cat config/public.crt >> config/cert.pem
rm config/private.key config/public.crt
```

If you have `libfaketime` installed, backdate for better Hue app compatibility (the official `install.sh` uses 2017):
```bash
faketime '2017-01-01 00:00:00' openssl req ...  # same command as above
```

## Launch

**The bridge MUST run on ports 80 and 443** for Hue apps to discover and connect. On macOS this requires `sudo`. Always launch with:

```bash
source .venv/bin/activate
cd BridgeEmulator

sudo .venv/bin/python3 HueEmulator3.py \
  --config_path ../config \
  --mac 84:2f:57:23:f9:32 \
  --debug
```

This uses the default ports (80 for HTTP, 443 for HTTPS) and auto-detects the bind IP. The `--config_path` points to `../config` when running from inside `BridgeEmulator/`.

**Important:** Ports other than 80/443 will NOT work with Hue apps. Apps discover the bridge via SSDP on port 1900/udp and hardcode port 80 for the API. Some third-party apps let you enter a custom IP:port, but official apps do not.

### Dev-only: non-privileged port (8080)

For quick development when you don't need app compatibility, you can run without `sudo` on port 8080. **Only the CLI and direct API calls will work — no app will discover or connect to the bridge:**

```bash
source .venv/bin/activate
cd BridgeEmulator

python3 HueEmulator3.py \
  --config_path ../config \
  --mac 84:2f:57:23:f9:32 \
  --http-port 8080 \
  --no-serve-https \
  --debug
```

**Flags explained**:

| Flag | Purpose |
|------|---------|
| `--config_path` | Where config YAML files and cert.pem live. Default `/opt/hue-emulator/config` (Linux path, doesn't exist on macOS) |
| `--mac` | Bridge MAC address. Required on macOS — the auto-detection uses Linux `ip` and `/sys/class/net` |
| `--http-port` | HTTP port. Default `80`. Override only for dev (see warning above) |
| `--https-port` | HTTPS port. Default `443` |
| `--no-serve-https` | Skip HTTPS entirely. Useful for dev |
| `--debug` | Verbose logging |
| `--bind-ip` | IP to listen on. Default `0.0.0.0` |
| `--no-link-button` | Skip link-button pairing (insecure — any app can connect) |

## Required ports

| Port | Protocol | Purpose |
|------|----------|---------|
| 80 | TCP | HTTP API |
| 443 | TCP | HTTPS API |
| 1900 | UDP | SSDP discovery |
| 2100 | UDP | SSDP/UPnP |
| 1982 | UDP | diyHue discovery |

Hue apps (official and third-party) discover the bridge via SSDP on port 1900/udp and expect the API on port 80. Using any other port breaks app compatibility — apps will not discover or connect to the bridge.

## Web UI

`http://<bridge-ip>` (e.g. `http://192.168.8.34`)

Default login: `admin@diyhue.org` — password is hashed in `config/config.yaml` (auto-generated on first run).

## macOS caveats

- **Ports 80/443 require `sudo`** — the bridge MUST run on these ports for app compatibility. Non-privileged ports (8080) only work for direct API access.
- **No `ip` command** — the MAC auto-detection in `argumentHandler.py` calls `ip -o addr` which is Linux-only. Always pass `--mac` explicitly with your real interface MAC from `ifconfig en0 | grep ether`.
- **No `faketime`** (by default) — `genCert.sh` uses it to backdate certs to 2017-01-01. Install via `brew install libfaketime` or pre-generate the cert manually as shown above.
- **No `coap-client`** (by default) — install via `brew install libcoap`. Used for certain Hue protocol features.
- **No `nmap`** (by default) — install via `brew install nmap`. Required for automatic light discovery.
- **No `/sys/class/net/`** — the `install.sh` and Docker entrypoint scripts read MAC from sysfs, which doesn't exist on macOS.
- **Docker is the officially supported method** — manual install is Linux-only and community-maintained. We run via Python directly for development.

## How the official Linux install works

For reference, `BridgeEmulator/install.sh` does the following on Linux:

1. Detects the network interface and reads its MAC from `/sys/class/net/<iface>/address`
2. Generates an EUI-64 certificate backdated to 2017-01-01 using `faketime` and the project's `openssl.conf`
3. Installs system deps: `unzip python3 python3-pip openssl bluez bluetooth libcoap3-bin faketime`
4. Downloads and extracts the diyHue release zip
5. Pip-installs `requirements.txt` with `--break-system-packages`
6. Copies all files to `/opt/hue-emulator/`
7. Downloads the latest diyHueUI release and extracts it into `flaskUI/`
8. Installs a systemd service (`hue-emulator.service`)
9. The systemd service runs: `python3 HueEmulator3.py --debug`
   (Config, cert, and MAC are already at `/opt/hue-emulator/config/`)
