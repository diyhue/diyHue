def rgbBrightness(rgb, brightness):
    r = sorted((0, int(rgb[0] * brightness) >> 8, 255))[1] #calculate with brightness and clamp
    g = sorted((0, int(rgb[1] * brightness) >> 8, 255))[1]
    b = sorted((0, int(rgb[2] * brightness) >> 8, 255))[1]
    return [r, g, b]

def clampRGB(rgb):
    r = sorted((0, int(rgb[0]), 255))[1]
    g = sorted((0, int(rgb[1]), 255))[1]
    b = sorted((0, int(rgb[2]), 255))[1]
    return [r, g, b]

def convert_rgb_xy(red, green, blue):
    red = pow((red + 0.055) / (1.0 + 0.055), 2.4) if red > 0.04045 else red / 12.92
    green = pow((green + 0.055) / (1.0 + 0.055), 2.4) if green > 0.04045 else green / 12.92
    blue = pow((blue + 0.055) / (1.0 + 0.055), 2.4) if blue > 0.04045 else blue / 12.92

#Convert the RGB values to XYZ using the Wide RGB D65 conversion formula The formulas used:
    X = red * 0.664511 + green * 0.154324 + blue * 0.162028
    Y = red * 0.283881 + green * 0.668433 + blue * 0.047685
    Z = red * 0.000088 + green * 0.072310 + blue * 0.986039

#Calculate the xy values from the XYZ values
    div = X + Y + Z
    if div < 0.000001:
        # set values to zero in case of div by zero
        x = 0
        y = 0
    else:
        x = X / div
        y = Y / div
    return [x, y]

def convert_xy(x, y, bri): #needed for milight hub that don't work with xy values
    X = x
    Y = y
    Z = 1.0 - x - y

  # sRGB D65 conversion
    r =  X * 3.2406 - Y * 1.5372 - Z * 0.4986
    g = -X * 0.9689 + Y * 1.8758 + Z * 0.0415
    b =  X * 0.0557 - Y * 0.2040 + Z * 1.0570


    r = 12.92 * r if r <= 0.0031308 else (1.0 + 0.055) * pow(r, (1.0 / 2.4)) - 0.055
    g = 12.92 * g if g <= 0.0031308 else (1.0 + 0.055) * pow(g, (1.0 / 2.4)) - 0.055
    b = 12.92 * b if b <= 0.0031308 else (1.0 + 0.055) * pow(b, (1.0 / 2.4)) - 0.055

    if r > b and r > g:
    # red is biggest
        if r > 1:
            g = g / r
            b = b / r
            r = 1
    elif g > b and g > r:
    # green is biggest
        if g > 1:
            r = r / g
            b = b / g
            g = 1

    elif b > r and b > g:
    # blue is biggest
        if b > 1:
            r = r / b
            g = g / b
            b = 1

    r = 0 if r < 0 else r
    g = 0 if g < 0 else g
    b = 0 if b < 0 else b
    return clampRGB([r * bri, g * bri, b * bri])

def hsv_to_rgb(h, s, v):
    """Convert Hue's hue (0-65535), sat (0-254) and bri (0-254) to an RGB list (0-255)."""
    s = float(s / 254)
    v = float(v / 254)
    c = v * s
    sector = (h % 65536) / 65536 * 6  # hue in sixths of the circle, 0 <= sector < 6
    x = c * (1 - abs(sector % 2 - 1))
    m = v - c
    if sector < 1:
        r, g, b = c, x, 0
    elif sector < 2:
        r, g, b = x, c, 0
    elif sector < 3:
        r, g, b = 0, c, x
    elif sector < 4:
        r, g, b = 0, x, c
    elif sector < 5:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    return clampRGB([round((r + m) * 255), round((g + m) * 255), round((b + m) * 255)])
