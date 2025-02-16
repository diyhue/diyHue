import json
import requests
import logManager
from functions.colors import convert_rgb_xy, convert_xy, hsv_to_rgb
from typing import List, Dict, Any

logging = logManager.logger.get_logger(__name__)

BASE_URL = "https://openapi.api.govee.com/router/api/v1"
BASE_TYPE = "devices.capabilities."

def get_headers() -> Dict[str, str]:
    """
    Get the headers required for Govee API requests.

    Returns:
        dict: Headers including API key and content type.
    """
    import configManager
    bridgeConfig = configManager.bridgeConfig.yaml_config
    return {
        "Govee-API-Key": bridgeConfig["config"]["govee"].get('api_key', ''),
        "Content-Type": "application/json"
    }

def is_json(content: str) -> bool:
    """
    Check if the content is valid JSON.

    Args:
        content (str): The content to check.

    Returns:
        bool: True if the content is valid JSON, False otherwise.
    """
    try:
        json.loads(content)
    except ValueError:
        return False
    return True

def discover(detectedLights: List[Dict[str, Any]]) -> None:
    """
    Discover Govee lights and append them to the detectedLights list.

    Args:
        detectedLights (list): List to append discovered lights to.
    """
    logging.debug("Govee: <discover> invoked!")
    try:
        response = requests.get(f"{BASE_URL}/user/devices", headers=get_headers())
        response.raise_for_status()
        if response.content and is_json(response.content):  # Check if response content is valid JSON
            devices = response.json().get("data", {})
            logging.debug(f"Govee: Found {len(devices)} devices")
            logging.debug(f"Govee: {devices}")
            for device in devices:
                device_id = device["device"]
                device_name = device.get("deviceName", f'{device["sku"]}-{device_id.replace(":","")[10:]}')
                capabilities = [function["type"] for function in device["capabilities"]]
                if has_capabilities(capabilities, ["on_off", "segment_color_setting"]):
                    handle_segmented_device(device, device_name, detectedLights)
                elif has_capabilities(capabilities, ["on_off", "color_setting"]):
                    handle_non_segmented_device(device, device_name, detectedLights)
    except requests.RequestException as e:
        logging.error("Error connecting to Govee: %s", e)
        return None

def has_capabilities(capabilities: List[str], required_capabilities: List[str]) -> bool:
    """
    Check if the device has the required capabilities.

    Args:
        capabilities (List[str]): List of capabilities the device has.
        required_capabilities (List[str]): List of required capabilities.

    Returns:
        bool: True if the device has all required capabilities, False otherwise.
    """
    return all(f"{BASE_TYPE}{cap}" in capabilities for cap in required_capabilities)

def handle_segmented_device(device: Dict[str, Any], device_name: str, detectedLights: List[Dict[str, Any]]) -> None:
    """
    Handle a segmented Govee device and append it to the detectedLights list.

    Args:
        device (Dict[str, Any]): The device information.
        device_name (str): The name of the device.
        detectedLights (List[Dict[str, Any]]): List to append the device to.
    """
    segments, bri_range = get_segmented_device_info(device)
    logging.debug(f"Govee: Found {device_name} with {segments} segments")
    for option in range(segments):
        detectedLights.append(create_light_entry(device, device_name, option, bri_range))

def get_segmented_device_info(device: Dict[str, Any]) -> tuple[int, Dict[str, Any]]:
    """
    Get the number of segments and brightness range for a segmented device.

    Args:
        device (Dict[str, Any]): The device information.

    Returns:
        tuple[int, Dict[str, Any]]: Number of segments and brightness range.
    """
    segments = 0
    bri_range = {}
    for function in device["capabilities"]:
        if function["type"] == f"{BASE_TYPE}segment_color_setting":
            segments = len(function['parameters']['fields'][0]['options'])
        if function["type"] == f"{BASE_TYPE}range" and "brightness" in function["instance"]:
            bri_range = function['parameters']['range']
    return segments, bri_range

def create_light_entry(device: Dict[str, Any], device_name: str, segment_id: int, bri_range: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a light entry for a Govee device.

    Args:
        device (Dict[str, Any]): The device information.
        device_name (str): The name of the device.
        segment_id (int): The segment ID.
        bri_range (Dict[str, Any]): The brightness range.

    Returns:
        Dict[str, Any]: The light entry.
    """
    return {
        "protocol": "govee",
        "name": f"{device_name}-seg{segment_id}" if segment_id >= 0 else device_name,
        "modelid": "LLC010",
        "protocol_cfg": {
            "device_id": device["device"],
            "sku_model": device["sku"],
            "segmentedID": segment_id,
            "bri_range": {
                "min": bri_range.get("min", 1),
                "max": bri_range.get("max", 100),
                "precision": bri_range.get("precision", 1)
            }
        }
    }

def handle_non_segmented_device(device: Dict[str, Any], device_name: str, detectedLights: List[Dict[str, Any]]) -> None:
    """
    Handle a non-segmented Govee device and append it to the detectedLights list.

    Args:
        device (Dict[str, Any]): The device information.
        device_name (str): The name of the device.
        detectedLights (List[Dict[str, Any]]): List to append the device to.
    """
    bri_range = get_brightness_range(device)
    detectedLights.append(create_light_entry(device, device_name, -1, bri_range))
    logging.debug(f"Govee: Found {device_name}")

def get_brightness_range(device: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get the brightness range for a device.

    Args:
        device (Dict[str, Any]): The device information.

    Returns:
        Dict[str, Any]: The brightness range.
    """
    for function in device["capabilities"]:
        if function["type"] == f"{BASE_TYPE}range" and "brightness" in function["instance"]:
            return function['parameters']['range']
    return {}

def set_light(light: Any, data: Dict[str, Any]) -> None:
    """
    Set the state of a Govee light.

    Args:
        light (Any): The light object containing protocol configuration.
        data (dict): The data containing state information to set.
    """
    for date_type in data:
        request_data = create_request_data(light, data, date_type)
        if request_data is not None:
            response = requests.put(f"{BASE_URL}/device/control", headers=get_headers(), data=json.dumps({"requestId": "1", "payload": request_data}))
            response.raise_for_status()

def create_request_data(light: Any, data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
    """
    Create the request data for setting the state of a Govee light.

    Args:
        light (Any): The light object containing protocol configuration.
        data (Dict[str, Any]): The data containing state information to set.
        data_type (str): The type of data to set.

    Returns:
        Dict[str, Any]: The request data.
    """
    device_id = light.protocol_cfg["device_id"]
    model = light.protocol_cfg["sku_model"]
    request_data = {"sku": model, "device": device_id}

    if data_type == "on":
        request_data["capability"] = create_on_off_capability(data["on"])
        return request_data

    elif data_type == "bri":
        request_data["capability"] = create_brightness_capability(data['bri'], light.protocol_cfg.get("segmentedID", -1), light.protocol_cfg.get("bri_range", {}))
        return request_data

    elif data_type == "xy":
        r, g, b = convert_xy(data['xy'][0], data['xy'][1], data.get('bri', 255))
        request_data["capability"] = create_color_capability(r, g, b, light.protocol_cfg.get("segmentedID", -1))
        return request_data

    elif data_type == "hue" or data_type == "sat":
        hue = data.get('hue', 0)
        sat = data.get('sat', 0)
        bri = data.get('bri', 255)
        r, g, b = hsv_to_rgb(hue, sat, bri)
        request_data["capability"] = create_color_capability(r, g, b, light.protocol_cfg.get("segmentedID", -1))
        return request_data

    else:
        return None

def create_on_off_capability(value: bool) -> Dict[str, Any]:
    """
    Create the on/off capability for a Govee light.

    Args:
        value (bool): The on/off value.

    Returns:
        Dict[str, Any]: The on/off capability.
    """
    return {
        "type": f"{BASE_TYPE}on_off",
        "instance": "powerSwitch",
        "value": value
    }

def create_brightness_capability(brightness: int, segment_id: int, bri_range: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create the brightness capability for a Govee light.

    Args:
        brightness (int): The brightness value.
        segment_id (int): The segment ID.
        bri_range (Dict[str, Any]): The brightness range.

    Returns:
        Dict[str, Any]: The brightness capability.
    """
    mapped_value = round(bri_range.get("min", 0) + ((brightness / 255) * (bri_range.get("max", 100) - bri_range.get("min", 0))),bri_range.get("precision", 0))
    if segment_id >= 0:
        return {
            "type": f"{BASE_TYPE}segment_color_setting",
            "instance": "segmentedBrightness",
            "value": {
                "segment": [segment_id],
                "brightness": mapped_value
            }
        }
    return {
        "type": f"{BASE_TYPE}range",
        "instance": "brightness",
        "value": mapped_value
    }

def create_color_capability(r: int, g: int, b: int, segment_id: int) -> Dict[str, Any]:
    """
    Create the color capability for a Govee light.

    Args:
        r (int): The red value.
        g (int): The green value.
        b (int): The blue value.
        segment_id (int): The segment ID.

    Returns:
        Dict[str, Any]: The color capability.
    """
    if segment_id >= 0:
        return {
            "type": f"{BASE_TYPE}segment_color_setting",
            "instance": "segmentedColorRgb",
            "value": {
                "segment": [segment_id],
                "rgb": (((r & 0xFF) << 16) | ((g & 0xFF) << 8) | ((b & 0xFF) << 0))
            }
        }
    return {
        "type": f"{BASE_TYPE}color_setting",
        "instance": "colorRgb",
        "value": (((r & 0xFF) << 16) | ((g & 0xFF) << 8) | ((b & 0xFF) << 0))
    }

def get_light_state(light: Any) -> Dict[str, Any]:
    """
    Get the current state of a Govee light.

    Args:
        light (Any): The light object containing protocol configuration.

    Returns:
        dict: The current state of the light.
    """
    response = requests.get(f"{BASE_URL}/device/state", headers=get_headers(), data=json.dumps({"requestId": "uuid", "payload": {"sku": light.protocol_cfg["sku_model"], "device": light.protocol_cfg["device_id"]}}))
    response.raise_for_status()
    return parse_light_state(response.json().get("payload", {}).get("capabilities", {}), light)

def parse_light_state(state_data: List[Dict[str, Any]], light: Any) -> Dict[str, Any]:
    """
    Parse the state data of a Govee light.

    Args:
        state_data (List[Dict[str, Any]]): The state data.
        light (Any): The light object containing protocol configuration.

    Returns:
        Dict[str, Any]: The parsed state data.
    """
    state = {}
    for function in state_data:
        if function["type"] == f"{BASE_TYPE}online":
            state["reachable"] = function["state"]["value"] == "true"
        if function["type"] == f"{BASE_TYPE}on_off":
            state["on"] = function["state"]["value"] == 1
        if function["type"] == f"{BASE_TYPE}range" and "brightness" in function["instance"]:
            state["bri"] = round(((function["state"]["value"] / light.protocol_cfg["bri_range"]["max"]) * 255))
        if function["type"] == f"{BASE_TYPE}color_setting":
            rgb = function["state"]["value"]
            state["xy"] = convert_rgb_xy((rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF)
    return state
