"""
Sensor type definitions for every supported Zigbee/MQTT device.

Each entry maps a model ID (as reported by Zigbee2MQTT) to one or more *sensor
types*.  A single physical device can expose multiple sensor types — for example
the Hue tap dial switch (RDM002) acts as both a button controller (ZLLSwitch)
and a rotary encoder (ZLLRelativeRotary).

The dict value for each sensor type contains three sections:
  - "state"  : the live values that change when the user interacts with the device
                (e.g. which button was pressed, current brightness level)
  - "config" : persistent settings reported by the device (battery %, reachability)
  - "static" : read-only hardware metadata sent to Hue apps (manufacturer, firmware)

MODEL_ALIASES maps alternative model IDs to the canonical one defined above.
Some devices are known to report a different model ID string than the canonical
name; both refer to the same hardware and share the same sensor configuration.
Exporting MODEL_ALIASES lets other modules (e.g. the MQTT service) stay in sync
without duplicating the list.
"""

sensorTypes = {}

sensorTypes["PHDL00"] = {
    "Daylight": {
        "state": {"daylight": None, "lastupdated": "none"},
        "config": {"on": True, "configured": False, "sunriseoffset": 30, "sunsetoffset": -30},
        "static": {"manufacturername": "Signify Netherlands B.V.", "swversion": "1.0"}
    }
}

sensorTypes["SML001"] = {
    "ZLLTemperature": {
        "state": {"temperature": 2100, "lastupdated": "none"},
        "config": {"on": False, "battery": 100, "reachable": True, "alert": "none", "ledindication": False, "usertest": False, "pending": []},
        "static": {"swupdate": {"state": "noupdates", "lastinstall": "2021-03-16T21:16:40Z"}, "manufacturername": "Signify Netherlands B.V.", "productname": "Hue temperature sensor", "swversion": "6.1.1.27575", "capabilities": {"certified": True, "primary": False}}
    },
    "ZLLPresence": {
        "state": {"lastupdated": "none", "presence": None},
        "config": {"on": False, "battery": 100, "reachable": True, "alert": "none", "ledindication": False, "usertest": False, "sensitivity": 2, "sensitivitymax": 2, "pending": []},
        "static": {"swupdate": {"state": "noupdates", "lastinstall": "2021-03-16T21:16:40Z"}, "manufacturername": "Signify Netherlands B.V.", "productname": "Hue motion sensor", "swversion": "6.1.1.27575", "capabilities": {"certified": True, "primary": True}}
    },
    "ZLLLightLevel": {
        "state": {"dark": True, "daylight": False, "lightlevel": 6000, "lastupdated": "none"},
        "config": {"on": False, "battery": 100, "reachable": True, "alert": "none", "tholddark": 9346, "tholdoffset": 7000, "ledindication": False, "usertest": False, "pending": []},
        "static": {"swupdate": {"state": "noupdates", "lastinstall": "2021-03-16T21:16:40Z"}, "manufacturername": "Signify Netherlands B.V.", "productname": "Hue ambient light sensor", "swversion": "6.1.1.27575", "capabilities": {"certified": True, "primary": False}}
    }
}

# Hue tap dial switch — 4 physical buttons (ZLLSwitch) + rotary encoder (ZLLRelativeRotary)
sensorTypes["RDM002"] = {
    "ZLLSwitch": {
        "state": {"buttonevent": 3002, "lastupdated": "2023-05-13T09:34:38Z"},
        "config": {"on": True, "battery": 100, "reachable": True, "pending": []},
        "static": {"swupdate": {"state": "noupdates", "lastinstall": "2022-07-01T14:38:51Z"}, "manufacturername": "Signify Netherlands B.V.", "productname": "Hue tap dial switch", "swversion": "2.59.25", "capabilities": {"certified": True, "primary": False, "inputs": [{"repeatintervals": [800], "events": [{"buttonevent": 1000, "eventtype": "initial_press"}, {"buttonevent": 1001, "eventtype": "repeat"}, {"buttonevent": 1002, "eventtype": "short_release"}, {"buttonevent": 1003, "eventtype": "long_release"}, {"buttonevent": 1010, "eventtype": "long_press"}]}, {"repeatintervals": [800], "events": [{"buttonevent": 2000, "eventtype": "initial_press"}, {"buttonevent": 2001, "eventtype": "repeat"}, {"buttonevent": 2002, "eventtype": "short_release"}, {"buttonevent": 2003, "eventtype": "long_release"}, {"buttonevent": 2010, "eventtype": "long_press"}]}, {"repeatintervals": [800], "events": [{"buttonevent": 3000, "eventtype": "initial_press"}, {"buttonevent": 3001, "eventtype": "repeat"}, {"buttonevent": 3002, "eventtype": "short_release"}, {"buttonevent": 3003, "eventtype": "long_release"}, {"buttonevent": 3010, "eventtype": "long_press"}]}, {"repeatintervals": [800], "events": [{"buttonevent": 4000, "eventtype": "initial_press"}, {"buttonevent": 4001, "eventtype": "repeat"}, {"buttonevent": 4002, "eventtype": "short_release"}, {"buttonevent": 4003, "eventtype": "long_release"}, {"buttonevent": 4010, "eventtype": "long_press"}]}]}}
    },
    "ZLLRelativeRotary": {
        "state": {"rotaryevent": 2, "expectedrotation": 90, "direction": "clock_wise", "rotary_step_size": 8, "expectedeventduration": 400, "lastupdated": "2023-05-13T09:34:38Z"},
        "config": {"on": True, "battery": 100, "reachable": True, "pending": []},
        "static": {"swupdate": {"state": "noupdates", "lastinstall": "2022-07-01T14:38:51Z"}, "manufacturername": "Signify Netherlands B.V.", "productname": "Hue tap dial switch", "swversion": "2.59.25", "capabilities": {"certified": True, "primary": False, "inputs": [{"repeatintervals": [400], "events": [{"rotaryevent": 1, "eventtype": "start"}, {"rotaryevent": 2, "eventtype": "repeat"}]}]}}
    }
}

# Hue dimmer switch (4-button, various regional variants)
sensorTypes["RWL021"] = {
    "ZLLSwitch": {
        "state": {"buttonevent": 4000, "lastupdated": "2022-11-13T09:34:38Z"},
        "config": {"on": True, "battery": None, "reachable": False, "pending": []},
        "static": {"swupdate": {"state": "noupdates", "lastinstall": "2022-11-13T09:32:55Z"}, "manufacturername": "Signify Netherlands B.V.", "productname": "Hue dimmer switch", "diversityid": "6426c751-c093-499e-afb6-9f0c863ec819", "swversion": "2.44.0_hBB3C188", "capabilities": {"certified": True, "primary": True, "inputs": [{"repeatintervals": [800], "events": [{"buttonevent": 1000, "eventtype": "initial_press"}, {"buttonevent": 1001, "eventtype": "repeat"}, {"buttonevent": 1002, "eventtype": "short_release"}, {"buttonevent": 1003, "eventtype": "long_release"}, {"buttonevent": 1010, "eventtype": "long_press"}]}, {"repeatintervals": [800], "events": [{"buttonevent": 2000, "eventtype": "initial_press"}, {"buttonevent": 2001, "eventtype": "repeat"}, {"buttonevent": 2002, "eventtype": "short_release"}, {"buttonevent": 2003, "eventtype": "long_release"}, {"buttonevent": 2010, "eventtype": "long_press"}]}, {"repeatintervals": [800], "events": [{"buttonevent": 3000, "eventtype": "initial_press"}, {"buttonevent": 3001, "eventtype": "repeat"}, {"buttonevent": 3002, "eventtype": "short_release"}, {"buttonevent": 3003, "eventtype": "long_release"}, {"buttonevent": 3010, "eventtype": "long_press"}]}, {"repeatintervals": [800], "events": [{"buttonevent": 4000, "eventtype": "initial_press"}, {"buttonevent": 4001, "eventtype": "repeat"}, {"buttonevent": 4002, "eventtype": "short_release"}, {"buttonevent": 4003, "eventtype": "long_release"}, {"buttonevent": 4010, "eventtype": "long_press"}]}]}}
    }
}

sensorTypes["ZGPSWITCH"] = {
    "ZGPSwitch": {
        "state": {"buttonevent": 0, "lastupdated": "none"},
        "config": {"on": True, "battery": 100, "reachable": True},
        "static": {"manufacturername": "Signify Netherlands B.V.", "swversion": ""}
    }
}

sensorTypes["TRADFRI remote control"] = {"ZHASwitch": {"state": {"buttonevent": 1002, "lastupdated": "none"}, "config": {"alert": "none", "battery": 90, "on": True, "reachable": True}, "static": {"swversion": "1.2.214", "manufacturername": "IKEA of Sweden"}}}
sensorTypes["TRADFRI on/off switch"] = {"ZHASwitch": {"state": {"buttonevent": 1002, "lastupdated": "none"}, "config": {"alert": "none", "battery": 90, "on": True, "reachable": True}, "static": {"swversion": "2.2.008", "manufacturername": "IKEA of Sweden"}}}
sensorTypes["TRADFRI wireless dimmer"] = {"ZHASwitch": {"state": {"buttonevent": 1002, "lastupdated": "none"}, "config": {"alert": "none", "battery": 90, "on": True, "reachable": True}, "static": {"swversion": "1.2.248", "manufacturername": "IKEA of Sweden"}}}

# ---------------------------------------------------------------------------
# Model aliases
# ---------------------------------------------------------------------------
# Maps every alternative model ID to its canonical sensorTypes key.
# Zigbee2MQTT may report a numeric OTA (over-the-air firmware) image identifier
# instead of the human-readable model name.  Both refer to the same hardware.
#
# This dict is exported so that other modules (e.g. the MQTT service) can
# register the same aliases for their own lookup tables without duplicating
# this list.
MODEL_ALIASES = {
    "RWL020": "RWL021",        # Hue dimmer switch (older EU hardware revision)
    "RWL022": "RWL021",        # Hue dimmer switch (newer hardware revision)
}

# Sensor types that are sub-components of another sensor's device in CLIP v2.
# These sensors share a uniqueid with their primary partner and need parent_id_v2 linking.
SUB_SENSOR_TYPES = {"ZLLRelativeRotary"}

for _alias, _canonical in MODEL_ALIASES.items():
    sensorTypes[_alias] = sensorTypes[_canonical]
