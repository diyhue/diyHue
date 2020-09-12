import logging
from time import sleep


def longPressButton(sensor, buttonevent):
    logging.info("long press detected")
    sleep(1)
    while bridge_config["sensors"][sensor]["state"]["buttonevent"] == buttonevent:
        logging.info("still pressed")
        current_time =  datetime.now()
        dxState["sensors"][sensor]["state"]["lastupdated"] = current_time
        rulesProcessor(["sensors",sensor], current_time)
        sleep(0.5)
    return
