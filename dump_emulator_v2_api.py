#!/usr/bin/env python3
"""
Script to dump V2 API responses from the diyHue emulator for analysis.
"""

import requests
import json
import sys
from urllib.parse import urljoin

def get_v2_resources(base_url, api_key):
    """Get all V2 resources from the emulator"""
    headers = {
        'hue-application-key': api_key
    }
    
    # List of V2 API resources to check
    resources = [
        'light', 'scene', 'smart_scene', 'grouped_light', 'room', 'zone',
        'entertainment', 'entertainment_configuration', 'zigbee_connectivity',
        'zigbee_device_discovery', 'device', 'device_power', 'geofence_client',
        'motion', 'light_level', 'temperature', 'relative_rotary', 'button',
        'bridge', 'bridge_home', 'homekit', 'geolocation', 'behavior_instance',
        'behavior_script'
    ]
    
    results = {}
    
    for resource in resources:
        try:
            url = urljoin(base_url, f'/clip/v2/resource/{resource}')
            response = requests.get(url, headers=headers, verify=False, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results[resource] = data
                print(f"✓ {resource}: {len(data.get('data', []))} items")
                
                # Show sample structure for first item
                if data.get('data') and len(data['data']) > 0:
                    sample = data['data'][0]
                    print(f"  Sample keys: {sorted(sample.keys())}")
                    
            else:
                print(f"✗ {resource}: HTTP {response.status_code}")
                results[resource] = None
                
        except Exception as e:
            print(f"✗ {resource}: Error - {e}")
            results[resource] = None
    
    return results

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 dump_emulator_v2_api.py <emulator_url> <api_key>")
        print("Example: python3 dump_emulator_v2_api.py https://127.0.0.1 e073b8e676b211f0abea722fe95fd7f5")
        sys.exit(1)
    
    emulator_url = sys.argv[1]
    api_key = sys.argv[2]
    
    print("Dumping V2 API responses from diyHue emulator")
    print("="*60)
    print(f"Emulator: {emulator_url}")
    
    # Get resources from emulator
    print("\nFetching resources...")
    resources = get_v2_resources(emulator_url, api_key)
    
    # Save detailed data
    print("\nSaving detailed data...")
    with open('emulator_v2_api_dump.json', 'w') as f:
        json.dump(resources, f, indent=2)
    
    print("Detailed dump saved to: emulator_v2_api_dump.json")
    
    # Show summary of structures
    print("\n" + "="*60)
    print("STRUCTURE SUMMARY")
    print("="*60)
    
    for resource_name, resource_data in resources.items():
        if not resource_data or 'data' not in resource_data:
            continue
            
        data = resource_data['data']
        if not data:
            continue
            
        sample_obj = data[0]
        print(f"\n{resource_name.upper()}:")
        print(f"  Keys: {sorted(sample_obj.keys())}")
        
        # Show some key values for important fields
        if 'id' in sample_obj:
            print(f"  ID: {sample_obj['id']}")
        if 'type' in sample_obj:
            print(f"  Type: {sample_obj['type']}")
        if 'metadata' in sample_obj and 'name' in sample_obj['metadata']:
            print(f"  Name: {sample_obj['metadata']['name']}")

if __name__ == "__main__":
    main()
