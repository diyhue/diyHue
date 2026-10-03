import requests
import subprocess
from datetime import datetime, timezone
from typing import List

import configManager
import logManager

bridgeConfig = configManager.bridgeConfig.yaml_config
logging = logManager.logger.get_logger(__name__)

def normalize_apiversion(apiversion: str) -> str:
    """Return major.minor.0 from an API version string.

    Philips used names like 1.72. Empty slices from a double dot ("6.1..0") are ignored.
    """
    parts = [part for part in str(apiversion).split(".") if part.isdigit()]
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[1]}.0"
    return str(apiversion)

def apiversion_from_version_name(version_name: str, swversion: str) -> str:
    """Build apiversion from a Philips versionName.

    versionName is either a short name ("1.72") or the full bridge version
    ("1.72.1967054020", and since September 2026 "6.1.1978418030").
    The first four characters are not a stable major.minor: "6.1.1978418030"[:4] is "6.1.".
    """
    name = str(version_name)
    build = str(swversion)
    if build and name.endswith(build):
        name = name[:-len(build)]
    return normalize_apiversion(name)

def bridge_software_version(apiversion: str, swversion: str) -> str:
    """CLIP v2 product_data.software_version, e.g. 1.72.1967054020 or 6.1.1978418030."""
    build = str(swversion)
    parts = [part for part in str(apiversion).split(".") if part.isdigit()]
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[1]}.{build}"
    return f"{apiversion}.{build}"

def versionCheck() -> None:
    """
    Check for firmware updates from Philips and update the bridge configuration if a new version is available.
    """
    swversion = str(bridgeConfig["config"]["swversion"])
    current_api = str(bridgeConfig["config"].get("apiversion", ""))
    normalized_api = normalize_apiversion(current_api)
    if normalized_api != current_api:
        logging.info(f"apiversion corrected, old: {current_api} new: {normalized_api}")
        bridgeConfig["config"]["apiversion"] = normalized_api
        configManager.bridgeConfig.mark_dirty("config")
    url = f"https://firmware.meethue.com/v1/checkupdate/?deviceTypeId=BSB002&version={swversion}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        device_data = response.json()
        if device_data["updates"]:
            new_version = str(device_data["updates"][-1]["version"])
            new_apiversion = apiversion_from_version_name(device_data["updates"][-1]["versionName"], new_version)
            if new_version > swversion:
                logging.info(f"swversion number update from Philips, old: {swversion} new: {new_version}")
                bridgeConfig["config"]["swversion"] = new_version
                bridgeConfig["config"]["apiversion"] = new_apiversion
                configManager.bridgeConfig.mark_dirty("config")
                update_swupdate2_timestamps()
            else:
                logging.info("swversion higher than Philips")
        else:
            logging.info("no swversion number update from Philips")
    except requests.RequestException as e:
        logging.error(f"No connection to Philips: {e}")

def githubCheck() -> None:
    """
    Check for updates on GitHub for both the main diyHue repository and the UI repository.
    Update the bridge configuration based on the availability of updates.
    """
    creation_time = get_file_creation_time("HueEmulator3.py")
    publish_time = get_github_publish_time("https://api.github.com/repos/diyhue/diyhue/branches/master")
    
    logging.debug(f"creation_time diyHue : {creation_time}")
    logging.debug(f"publish_time  diyHue : {publish_time}")

    if publish_time > creation_time:
        logging.info("update on github")
        bridgeConfig["config"]["swupdate2"]["state"] = "allreadytoinstall"
    elif githubUICheck():
        logging.info("UI update on github")
        bridgeConfig["config"]["swupdate2"]["state"] = "anyreadytoinstall"
    else:
        logging.info("no update for diyHue or UI on github")
        bridgeConfig["config"]["swupdate2"]["state"] = "noupdates"
        bridgeConfig["config"]["swupdate2"]["bridge"]["state"] = "noupdates"

    bridgeConfig["config"]["swupdate2"]["checkforupdate"] = False

def githubUICheck() -> bool:
    """
    Check for updates on the GitHub UI repository.
    
    Returns:
        bool: True if there is a new update available, False otherwise.
    """
    creation_time = get_file_creation_time("flaskUI/templates/index.html")
    publish_time = get_github_publish_time("https://api.github.com/repos/diyhue/diyHueUI/releases/latest")
    
    logging.debug(f"creation_time UI : {creation_time}")
    logging.debug(f"publish_time  UI : {publish_time}")

    return publish_time > creation_time

def get_file_creation_time(filepath: str) -> str:
    """
    Get the creation time of a file.
    
    Args:
        filepath (str): The path to the file.
    
    Returns:
        str: The creation time of the file in the format "%Y-%m-%d %H".
    """
    try:
        creation_time = subprocess.run(f"stat -c %y {filepath}", shell=True, capture_output=True, text=True)
        creation_time_arg1 = creation_time.stdout.replace(".", " ").split(" ") if creation_time.stdout else "2999-01-01 01:01:01.000000000 +0100\n".replace(".", " ").split(" ")
        return parse_creation_time(creation_time_arg1)
    except subprocess.SubprocessError as e:
        logging.error(f"Error getting file creation time: {e}")
        return "2999-01-01 01:01:01"

def get_github_publish_time(url: str) -> str:
    """
    Get the publish time of the latest commit or release from a GitHub repository.
    
    Args:
        url (str): The API URL to fetch the publish time from.
    
    Returns:
        str: The publish time in the format "%Y-%m-%d %H".
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        device_data = response.json()
        if "commit" in device_data:
            return datetime.strptime(device_data["commit"]["commit"]["author"]["date"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H")
        elif "published_at" in device_data:
            return datetime.strptime(device_data["published_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H")
    except requests.RequestException as e:
        logging.error(f"No connection to GitHub: {e}")
        return "1970-01-01 00:00:00"

def parse_creation_time(creation_time_arg1: List[str]) -> str:
    """
    Parse the creation time from the output of the stat command.
    
    Args:
        creation_time_arg1 (List[str]): The list of strings representing the creation time.
    
    Returns:
        str: The parsed creation time in the format "%Y-%m-%d %H".
    """
    try:
        if len(creation_time_arg1) < 4:
            creation_time = f"{creation_time_arg1[0]} {creation_time_arg1[1]}".replace('\n', '')
            return datetime.strptime(creation_time, "%Y-%m-%d %H:%M:%S").astimezone(timezone.utc).strftime("%Y-%m-%d %H")
        else:
            creation_time = f"{creation_time_arg1[0]} {creation_time_arg1[1]} {creation_time_arg1[3]}".replace('\n', '')
            return datetime.strptime(creation_time, "%Y-%m-%d %H:%M:%S %z").astimezone(timezone.utc).strftime("%Y-%m-%d %H")
    except ValueError as e:
        logging.error(f"Error parsing creation time: {e}")
        return "2999-01-01 01:01:01"

def update_swupdate2_timestamps() -> None:
    """
    Update the timestamps for the last change and last install in the bridge configuration.
    """
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    bridgeConfig["config"]["swupdate2"]["lastchange"] = current_time
    bridgeConfig["config"]["swupdate2"]["bridge"]["lastinstall"] = current_time

def githubInstall() -> None:
    """
    Install updates from GitHub if they are ready to be installed.
    """
    if bridgeConfig["config"]["swupdate2"]["state"] in ["allreadytoinstall", "anyreadytoinstall"]:
        subprocess.Popen(f"sh githubInstall.sh {bridgeConfig['config']['ipaddress']} {bridgeConfig['config']['swupdate2']['state']}", shell=True, close_fds=True)
        bridgeConfig["config"]["swupdate2"]["state"] = "installing"

def startupCheck() -> None:
    """
    Perform a startup check for updates.
    """
    if bridgeConfig["config"]["swupdate2"]["install"]:
        bridgeConfig["config"]["swupdate2"]["install"] = False
        update_swupdate2_timestamps()
    versionCheck()
    githubCheck()
