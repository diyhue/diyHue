# diyHue Installation Guide for macOS

This guide will help you install and run the diyHue Hue Bridge emulator on macOS using Homebrew.

## Prerequisites

- macOS with Homebrew installed
- Python 3.7+ (already installed on macOS)
- Git (for cloning the repository)

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/diyhue/diyHue.git
cd diyHue
```

### 2. Install System Dependencies

Install required system packages using Homebrew:

```bash
# Install libcoap (for CoAP protocol support)
brew install libcoap

# Install libfaketime (for time manipulation)
brew install libfaketime
```

### 3. Create Python Virtual Environment

Create a virtual environment to avoid conflicts with system Python packages:

```bash
python3 -m venv diyhue_env
```

### 4. Install Python Dependencies

Activate the virtual environment and install required Python packages:

```bash
source diyhue_env/bin/activate
pip install -r requirements.txt
```

### 5. Verify Installation

Check if all required packages are installed:

```bash
python3 check_requirements.py
```

You should see all packages marked with ✅.

## Running the Emulator

### Option 1: Using the Runner Script (Recommended)

```bash
./run_emulator.sh
```

### Option 2: Manual Activation

```bash
source diyhue_env/bin/activate
python3 BridgeEmulator/HueEmulator3.py
```

### Common Command Line Options

```bash
# Basic run
python3 BridgeEmulator/HueEmulator3.py

# Enable debug output
python3 BridgeEmulator/HueEmulator3.py --debug

# Custom HTTP port
python3 BridgeEmulator/HueEmulator3.py --http-port 8080

# Docker mode
python3 BridgeEmulator/HueEmulator3.py --docker

# Custom bind IP
python3 BridgeEmulator/HueEmulator3.py --bind-ip 0.0.0.0

# Disable HTTPS (HTTP only)
python3 BridgeEmulator/HueEmulator3.py --no-serve-https
```

## Configuration

The emulator will create configuration files in the `BridgeEmulator/configManager/` directory on first run.

### Web Interface

Once running, access the web interface at:
- HTTP: `http://localhost:80` (or your custom port)
- HTTPS: `https://localhost:443` (if enabled)

### Adding Lights

1. Open the web interface
2. Go to the "Devices" section
3. Click "Add Light"
4. Choose your light type and follow the setup instructions

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   - Change the port using `--http-port` or `--https-port`
   - Check what's using the port: `lsof -i :80`

2. **Permission Denied**
   - Make sure the runner script is executable: `chmod +x run_emulator.sh`

3. **Missing Dependencies**
   - Run `python3 check_requirements.py` to verify all packages
   - Reinstall: `source diyhue_env/bin/activate && pip install -r requirements.txt`

4. **Virtual Environment Issues**
   - Delete and recreate: `rm -rf diyhue_env && python3 -m venv diyhue_env`

### Logs

Enable debug output to see detailed logs:

```bash
python3 BridgeEmulator/HueEmulator3.py --debug
```

## System Requirements

- **Minimum**: 512MB RAM, 1GB storage
- **Recommended**: 1GB+ RAM, 2GB+ storage
- **OS**: macOS 10.15+ (Catalina and later)

## Updating

To update the emulator:

```bash
git pull
source diyhue_env/bin/activate
pip install -r requirements.txt
```

## Support

- **Documentation**: [diyhue.readthedocs.io](https://diyhue.readthedocs.io/)
- **GitHub**: [github.com/diyhue/diyHue](https://github.com/diyhue/diyHue)
- **Discourse**: [diyhue.discourse.group](https://diyhue.discourse.group/)

## License

This project is open source. See [LICENSE.md](LICENSE.md) for details.
