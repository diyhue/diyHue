#!/usr/bin/env python3
"""
diyHue Requirements Checker
This script checks if all required Python packages are installed
"""

import sys
import importlib

def check_package(package_name, import_name=None):
    """Check if a package is installed"""
    if import_name is None:
        import_name = package_name
    
    try:
        importlib.import_module(import_name)
        print(f"✅ {package_name}")
        return True
    except ImportError:
        print(f"❌ {package_name} - NOT INSTALLED")
        return False

def main():
    print("diyHue Requirements Check")
    print("=" * 40)
    
    # List of required packages with their import names
    required_packages = [
        ("astral", "astral"),
        ("ws4py", "ws4py"),
        ("requests", "requests"),
        ("paho-mqtt", "paho.mqtt"),
        ("email-validator", "email_validator"),
        ("flask", "flask"),
        ("flask-login", "flask_login"),
        ("flask-restful", "flask_restful"),
        ("flask-wtf", "flask_wtf"),
        ("jsonify", "jsonify"),
        ("Werkzeug", "werkzeug"),
        ("WTForms", "wtforms"),
        ("pyyaml", "yaml"),
        ("zeroconf", "zeroconf"),
        ("flask-cors", "flask_cors"),
        ("yeelight", "yeelight"),
        ("python-kasa", "kasa"),
        ("bleak", "bleak"),
        ("rgbxy", "rgbxy"),
    ]
    
    print("Checking Python packages...")
    print("-" * 40)
    
    all_installed = True
    for package, import_name in required_packages:
        if not check_package(package, import_name):
            all_installed = False
    
    print("-" * 40)
    
    if all_installed:
        print("🎉 All required Python packages are installed!")
        print("\nYou can now run the Hue emulator with:")
        print("  ./run_emulator.sh")
        print("  or")
        print("  source diyhue_env/bin/activate && python3 BridgeEmulator/HueEmulator3.py")
    else:
        print("❌ Some packages are missing!")
        print("\nTo install missing packages, run:")
        print("  source diyhue_env/bin/activate && pip install -r requirements.txt")
        sys.exit(1)

if __name__ == "__main__":
    main()
