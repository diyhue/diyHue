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
    x = X / (X + Y + Z)
    y = Y / (X + Y + Z)
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
    s = float(s / 254)
    v = float(v / 254)
    c=v*s
    x=c*(1-abs(((h/11850)%2)-1))
    m=v-c
    if h>=0 and h<10992:
        r=c
        g=x
        b=0
    elif h>=10992 and h<21845:
        r=x
        g=c
        b=0
    elif h>=21845 and h<32837:
        r = 0
        g = c
        b = x
    elif h>=32837 and h<43830:
        r = 0
        g = x
        b = c
    elif h>=43830 and h<54813:
        r = x
        g = 0
        b = c
    else:
        r = c
        g = 0
        b = x

    return clampRGB([r * 255, g * 255, b * 255])
