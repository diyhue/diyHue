#!/bin/bash

# diyHue Emulator Runner Script
# This script activates the virtual environment and runs the Hue emulator

echo "Starting diyHue Hue Bridge Emulator..."
echo "======================================"

# Check if virtual environment exists
if [ ! -d "diyhue_env" ]; then
    echo "Error: Virtual environment 'diyhue_env' not found!"
    echo "Please run: python3 -m venv diyhue_env"
    echo "Then run: source diyhue_env/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source diyhue_env/bin/activate

# Check if all required packages are installed
echo "Checking required packages..."
python3 -c "
import sys
import importlib

required_packages = ['flask', 'flask_login', 'flask_restful', 'flask_wtf', 'requests', 'paho.mqtt', 'astral', 'ws4py', 'yeelight', 'bleak', 'rgbxy']

missing_packages = []
for package in required_packages:
    try:
        importlib.import_module(package)
    except ImportError:
        missing_packages.append(package)

if missing_packages:
    print(f'Missing packages: {', '.join(missing_packages)}')
    sys.exit(1)
else:
    print('All required packages are installed!')
    sys.exit(0)
"

if [ $? -ne 0 ]; then
    echo "Error: Some required packages are missing!"
    echo "Please run: source diyhue_env/bin/activate && pip install -r requirements.txt"
    exit 1
fi

echo "Starting Hue Emulator..."
echo ""
echo "Usage examples:"
echo "  Basic run: python3 BridgeEmulator/HueEmulator3.py"
echo "  With debug: python3 BridgeEmulator/HueEmulator3.py --debug"
echo "  Custom port: python3 BridgeEmulator/HueEmulator3.py --http-port 8080"
echo "  Docker mode: python3 BridgeEmulator/HueEmulator3.py --docker"
echo ""
echo "Press Ctrl+C to stop the emulator"
echo "======================================"

# Run the emulator with any provided arguments
python3 BridgeEmulator/HueEmulator3.py "$@"
