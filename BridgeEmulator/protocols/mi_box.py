import logging, binascii, socket, colorsys, time
from functions.colors import convert_rgb_xy, convert_xy, rgbBrightness

#todo: add support for multiple mi boxes? these globals don't look nice
commandCounter = 0
sessionId1 = 0
sessionId2 = 0
sock = None
lastSentMessageTime = 0
prevOn = False

def set_light(address, light, data, rgb = None):
    global prevOn
    
    # Assign all data elements to the "Object" light.
    for key, value in data.items():
        light["state"][key] = value

    on = light["state"]["on"]
    colormode = light["state"]["colormode"]
    
    if (on != prevOn):
        sendOnCmd(address)
    
    if(('xy' in data) or ('ct' in data) or rgb):
        if (colormode == "xy"):
            if rgb: # this one is more performant than the "else" block
                r, g, b = rgbBrightness(rgb, light["state"]["bri"])
            else:
                xy = light["state"]["xy"]
                r, g, b = convert_xy(xy[0], xy[1], light["state"]["bri"])
            (hue, saturation, value) = colorsys.rgb_to_hsv(r,g,b)
            sendHueCmd(address, hue*255)
            sendSaturationCmd(address, (1-saturation)*100)
        elif colormode == "ct":
            ct = light["state"]["ct"]
            ct01 = (ct - 153) / (500 - 153) # map color temperature from 153-500 to 0-1
            sendKelvinCmd(address, (1-ct01)*100) 

    if("bri" in data):
        sendBrightnessCmd(address, (light["state"]["bri"]/255)*100)
    
    if not on:
        sendOffCmd(address)

    prevOn = on  

def get_lightType(address):
    light_type = address["light_type"]
    if(light_type == "rgbcct"):
        light_type = "rgbww"
    return light_type

def bytesToHexStr(b):
    hex_data = binascii.hexlify(b)
    return hex_data.decode('utf-8')

def sendMsg(address, msg):
    global sock
    logging.info("sending udp message to MiLight box:"+bytesToHexStr(msg))
    if sock is None:
        logging.info("creating socket")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)
        logging.info("connecting to ip")
        sock.connect((address["ip"], address["port"]))

    logging.info("sock.sendall")
    sock.sendall(msg)

def closeSocket():
    global sock, commandCounter, sessionId1, sessionId2, lastSentMessageTime
    if sock is not None:
        logging.info("force closing socket connection")
        sock.close()
    sock = None
    sessionId1 = 0
    sessionId2 = 0
    commandCounter = 0

def sendCmd(address, cmd, tries=3):
    global sock, commandCounter, sessionId1, sessionId2, lastSentMessageTime
    logging.info("sendcommand"+bytesToHexStr(cmd))
    #todo: prevent sending multiple commands at once, this will start the session id request multiple times

    now = time.time()
    if now - lastSentMessageTime > 10:
        closeSocket()
        logging.info("creating new socket connection to MiLight box")
    lastSentMessageTime = now

    commandCounter += 1
    if commandCounter > 255:
        commandCounter = 0

    group = address["group"]
    light_type = get_lightType(address)

    if sessionId1 == 0 and sessionId2 == 0:
        if not getSessionId(address):
            return False

    msg = b'\x80\x00\x00\x00\x11'
    msg += bytes([sessionId1, sessionId2])
    msg += b'\x00'
    msg += bytes([commandCounter])
    msg += b'\x00'
    headersLen = len(msg)

    msg += b'\x31\x00\x00'
    if light_type == "rgbww":
        msg += b'\x08'
    elif light_type == "rgbw":
        msg += b'\x07'
    else:
        msg += b'\x00'
    msg += cmd
    msg += bytes([group])
    msg += b'\x00'

    # calculate checksum
    crc = 0
    for i in range(len(msg) - headersLen):
        crc = (crc + msg[headersLen+i]) & 255
    msg += bytes([crc])

    sendMsg(address, msg)
    
    logging.info("wait for receiving after sending command")
    data = None
    try:
         #pylint: disable=unused-variable
        data, recvAddr = sock.recvfrom(1024)
    except socket.timeout:
        logging.info("socket timed out")
    receiveConfirmed = False
    if data is not None:
        logging.info("received "+bytesToHexStr(data))
        if len(data) == 8 and data[-1] == 0:
            logging.info("command receive confirmed")
            receiveConfirmed = True
    if receiveConfirmed:
        return
    if tries >= 1:
        logging.info("retrying sending command")
        tries -= 1
        closeSocket()
        sendCmd(address, cmd, tries)
    else:
        raise Exception("sending command failed after 3 tries")

def getSessionId(address):
    global sessionId1, sessionId2
    sendMsg(address, b'\x20\x00\x00\x00\x16\x02\x62\x3A\xD5\xED\xA3\x01\xAE\x08\x2D\x46\x61\x41\xA7\xF6\xDC\xAF\xD3\xE6\x00\x00\x1E')
    totalTries = 0
    while totalTries < 3:
        totalTries+=1
        logging.info("wait for receiving session id")
        data, address = sock.recvfrom(1024)
        if len(data) == 22:
            data = bytes(data)
            sessionId1 = data[19]
            sessionId2 = data[20]
            return True
    return False

def sendOnCmd(address):
    light_type = get_lightType(address)
    cmd = b'' 
    if light_type == "rgbww":
        cmd += b'\x04\x01'
    elif light_type == "rgbw":
        cmd += b'\x03\x01'
    else:
        cmd += b'\x03\x03'
    cmd += b'\x00\x00\x00'
    sendCmd(address, cmd)

def sendOffCmd(address):
    light_type = get_lightType(address)
    cmd = b''
    if light_type == "rgbww":
        cmd += b'\x04\x02'
    elif light_type == "rgbw":
        cmd += b'\x03\x02'
    else:
        cmd += b'\x03\x04'
    cmd += b'\x00\x00\x00'
    sendCmd(address, cmd)

#brightness is between 0-100
def sendBrightnessCmd(address, brightness):
    light_type = get_lightType(address)
    cmd = b''
    if light_type == "rgbww":
        cmd += b'\x03'
    elif light_type == "rgbw":
        cmd += b'\x02'
    else:
        cmd += b'\x02'
    cmd += bytes([int(brightness)])
    cmd += b'\x00\x00\x00'
    sendCmd(address, cmd, 0)

#hue is between 0-255
def sendHueCmd(address, hue):
    cmd = b'\x01'
    hue = int(hue) + 10 # Color correction.
    if (hue > 255):
        hue = hue - 255
        
    cmd += bytes([hue] * 4)
    sendCmd(address, cmd, 0)

#saturation is between 0-100
def sendSaturationCmd(address, saturation):
    cmd = b'\x02'
    #todo: not sure if \x02 works with rgbw and hub lights,
    #I don't have the hardware so I can't test which bytes are needed here
    saturation = int(saturation)
    cmd += bytes([saturation])
    cmd += b'\x00\x00\x00'
    sendCmd(address, cmd, 0)

#kelvin is between 0-100
def sendKelvinCmd(address, kelvin):
    cmd = b'\x05'
    kelvin = int(kelvin)
    cmd += bytes([kelvin])
    cmd += b'\x00\x00\x00'
    sendCmd(address, cmd, 0)

def get_light_state(address, light):
    return {}
