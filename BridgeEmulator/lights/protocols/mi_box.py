import logging, binascii, socket, colorsys, time
from functions.colors import convert_xy, rgbBrightness

#todo: add support for multiple mi boxes? these globals don't look nice
commandCounter = 0
sessionId1 = 0
sessionId2 = 0
sock = None
lastSentMessageTime = 0

def set_light(light, data, rgb = None):
	for key, value in data.items():
		light.state[key] = value

	on = light.state["on"]
	if on:
		sendOnCmd(light)
	colormode = light.state["colormode"]
	if colormode == "xy":
		xy = light.state["xy"]
		if rgb:
			r, g, b = rgbBrightness(rgb, light.state["bri"])
		else:
			r, g, b = convert_xy(xy[0], xy[1], light.state["bri"])
		(hue, saturation, value) = colorsys.rgb_to_hsv(r,g,b)
		sendHueCmd(light, hue*255)
		sendSaturationCmd(light, (1-saturation)*100)
	elif colormode == "ct":
		ct = light.state["ct"]
		ct01 = (ct - 153) / (500 - 153) #map color temperature from 153-500 to 0-1
		sendKelvinCmd(light, (1-ct01)*100)

	sendBrightnessCmd(light, (light.state["bri"]/255)*100)
	if not on:
		sendOffCmd(light)

def bytesToHexStr(b):
	hex_data = binascii.hexlify(b)
	return hex_data.decode('utf-8')

def sendMsg(light, msg):
	global sock
	logging.info("sending udp message to MiLight box:"+bytesToHexStr(msg))
	if sock is None:
		logging.info("creating socket")
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.settimeout(0.5)
		logging.info("connecting to ip")
		sock.connect((light.protocol_cfg["ip"], light.protocol_cfg["port"]))

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

def sendCmd(light, cmd, tries=3):
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

	ip = light.protocol_cfg["ip"]
	group = light.protocol_cfg["group"]
	light_type = light.protocol_cfg["light_type"]

	if sessionId1 == 0 and sessionId2 == 0:
		if not getSessionId(light):
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

	#calculate checksum
	crc = 0
	for i in range(len(msg) - headersLen):
		crc = (crc + msg[headersLen+i]) & 255
	msg += bytes([crc])

	sendMsg(light, msg)
	logging.info("wait for receiving after sending command")
	data = None
	try:
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
	if tries > 1:
		logging.info("retrying sending command")
		tries -= 1
		closeSocket()
		sendCmd(light, cmd, tries)
	else:
		raise Exception("sending command failed after 3 tries")

def getSessionId(light):
	global sessionId1, sessionId2
	sendMsg(light, b'\x20\x00\x00\x00\x16\x02\x62\x3A\xD5\xED\xA3\x01\xAE\x08\x2D\x46\x61\x41\xA7\xF6\xDC\xAF\xD3\xE6\x00\x00\x1E')
	totalTries = 0
	while totalTries < 3:
		totalTries+=1
		logging.info("wait for receiving session id")
		data, light = sock.recvfrom(1024)
		if len(data) == 22:
			data = bytes(data)
			sessionId1 = data[19]
			sessionId2 = data[20]
			return True
	return False

def sendOnCmd(light):
	light_type = light.protocol_cfg["light_type"]
	cmd = b''
	if light_type == "rgbww":
		cmd += b'\x04\x01'
	elif light_type == "rgbw":
		cmd += b'\x03\x01'
	else:
		cmd += b'\x03\x03'
	cmd += b'\x00\x00\x00'
	sendCmd(light, cmd)

def sendOffCmd(light):
	light_type = light.protocol_cfg["light_type"]
	cmd = b''
	if light_type == "rgbww":
		cmd += b'\x04\x02'
	elif light_type == "rgbw":
		cmd += b'\x03\x02'
	else:
		cmd += b'\x03\x04'
	cmd += b'\x00\x00\x00'
	sendCmd(light, cmd)

#brightness is between 0-100
def sendBrightnessCmd(light, brightness):
	light_type = light.protocol_cfg["light_type"]
	cmd = b''
	if light_type == "rgbww":
		cmd += b'\x03'
	elif light_type == "rgbw":
		cmd += b'\x02'
	else:
		cmd += b'\x02'
	cmd += bytes([int(brightness)])
	cmd += b'\x00\x00\x00'
	sendCmd(light, cmd)

#hue is between 0-255
def sendHueCmd(light, hue):
	cmd = b'\x01'
	hue = int(hue)
	cmd += bytes([hue] * 4)
	sendCmd(light, cmd)

#saturation is between 0-100
def sendSaturationCmd(light, saturation):
	cmd = b'\x02'
	#todo: not sure if \x02 works with rgbw and hub lights,
	#I don't have the hardware so I can't test which bytes are needed here
	saturation = int(saturation)
	cmd += bytes([saturation])
	cmd += b'\x00\x00\x00'
	sendCmd(light, cmd)

#kelvin is between 0-100
def sendKelvinCmd(light, kelvin):
	cmd = b'\x05'
	kelvin = int(kelvin)
	cmd += bytes([kelvin])
	cmd += b'\x00\x00\x00'
	sendCmd(light, cmd)

def get_light_state(light):
	return 
