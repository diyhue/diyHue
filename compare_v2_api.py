#!/usr/bin/env python3
"""
Script to compare V2 API responses between diyHue emulator and original Hue Bridge
to identify missing or extra keys that might cause compatibility issues.
"""

import requests
import json
import sys
from urllib.parse import urljoin

def get_v2_resources(base_url, api_key):
    """Get all V2 resources from a bridge"""
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
            else:
                print(f"✗ {resource}: HTTP {response.status_code}")
                results[resource] = None
                
        except Exception as e:
            print(f"✗ {resource}: Error - {e}")
            results[resource] = None
    
    return results

def analyze_object_structure(resources_data):
    """Analyze the structure of objects in the resources"""
    structures = {}
    
    for resource_name, resource_data in resources_data.items():
        if not resource_data or 'data' not in resource_data:
            continue
            
        data = resource_data['data']
        if not data:
            continue
            
        # Get the first object as a sample
        sample_obj = data[0]
        structures[resource_name] = {
            'keys': sorted(sample_obj.keys()),
            'sample': sample_obj
        }
    
    return structures

def compare_structures(emulator_structures, original_structures):
    """Compare structures between emulator and original bridge"""
    print("\n" + "="*80)
    print("STRUCTURE COMPARISON")
    print("="*80)
    
    all_resources = set(emulator_structures.keys()) | set(original_structures.keys())
    
    for resource in sorted(all_resources):
        print(f"\n{resource.upper()}:")
        print("-" * len(resource))
        
        if resource not in emulator_structures:
            print("  ❌ Missing in emulator")
            continue
            
        if resource not in original_structures:
            print("  ❌ Missing in original bridge")
            continue
        
        emu_keys = set(emulator_structures[resource]['keys'])
        orig_keys = set(original_structures[resource]['keys'])
        
        missing_in_emu = orig_keys - emu_keys
        extra_in_emu = emu_keys - orig_keys
        common_keys = emu_keys & orig_keys
        
        if missing_in_emu:
            print(f"  ❌ Missing in emulator: {sorted(missing_in_emu)}")
        
        if extra_in_emu:
            print(f"  ⚠️  Extra in emulator: {sorted(extra_in_emu)}")
        
        if not missing_in_emu and not extra_in_emu:
            print(f"  ✅ Perfect match ({len(common_keys)} keys)")
        elif not missing_in_emu:
            print(f"  ✅ All required keys present ({len(common_keys)} common, {len(extra_in_emu)} extra)")
        else:
            print(f"  ❌ Missing required keys ({len(common_keys)} common, {len(missing_in_emu)} missing)")

def main():
    if len(sys.argv) != 5:
        print("Usage: python3 compare_v2_api.py <emulator_url> <emulator_api_key> <original_bridge_url> <original_bridge_api_key>")
        print("Example: python3 compare_v2_api.py https://127.0.0.1 e073b8e676b211f0abea722fe95fd7f5 https://192.168.10.52 e073b8e676b211f0abea722fe95fd7f5")
        sys.exit(1)
    
    emulator_url = sys.argv[1]
    emulator_key = sys.argv[2]
    original_url = sys.argv[3]
    original_key = sys.argv[4]
    
    print("Comparing V2 API responses between diyHue emulator and original Hue Bridge")
    print("="*80)
    
    print(f"\nEmulator: {emulator_url}")
    print(f"Original: {original_url}")
    
    # Get resources from emulator
    print("\nFetching resources from emulator...")
    emulator_resources = get_v2_resources(emulator_url, emulator_key)
    
    # Get resources from original bridge
    print("\nFetching resources from original bridge...")
    original_resources = get_v2_resources(original_url, original_key)
    
    # Analyze structures
    print("\nAnalyzing object structures...")
    emulator_structures = analyze_object_structure(emulator_resources)
    original_structures = analyze_object_structure(original_resources)
    
    # Compare structures
    compare_structures(emulator_structures, original_structures)
    
    # Save detailed data for manual inspection
    print("\nSaving detailed data...")
    
    with open('emulator_v2_api_dump.json', 'w') as f:
        json.dump(emulator_resources, f, indent=2)
    
    with open('original_bridge_v2_api_dump.json', 'w') as f:
        json.dump(original_resources, f, indent=2)
    
    print("Detailed dumps saved to:")
    print("  - emulator_v2_api_dump.json")
    print("  - original_bridge_v2_api_dump.json")

if __name__ == "__main__":
    main()
