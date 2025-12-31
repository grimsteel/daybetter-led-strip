import struct

RgbColor = tuple[int, int, int]

# Derived from the FastLED 16 bit gamma lookup table
GAMMA_CORRECTION = [
      0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
      0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   1,
      1,   1,   1,   1,   1,   1,   1,   1,   2,   2,   2,   2,   2,   2,   2,   3,
      3,   3,   3,   3,   4,   4,   4,   4,   4,   5,   5,   5,   5,   6,   6,   6,
      7,   7,   7,   7,   8,   8,   8,   9,   9,   9,  10,  10,  11,  11,  11,  12,
     12,  12,  13,  13,  14,  14,  15,  15,  16,  16,  17,  17,  18,  18,  19,  19,
     20,  20,  21,  21,  22,  23,  23,  24,  24,  25,  26,  26,  27,  28,  28,  29,
     30,  30,  31,  32,  33,  33,  34,  35,  36,  36,  37,  38,  39,  40,  40,  41,
     42,  43,  44,  45,  46,  47,  48,  48,  49,  50,  51,  52,  53,  54,  55,  56,
     57,  58,  60,  61,  62,  63,  64,  65,  66,  67,  68,  70,  71,  72,  73,  74,
     76,  77,  78,  79,  81,  82,  83,  85,  86,  87,  89,  90,  91,  93,  94,  96,
     97,  99, 100, 102, 103, 105, 106, 108, 109, 111, 112, 114, 115, 117, 119, 120,
    122, 124, 125, 127, 129, 130, 132, 134, 136, 137, 139, 141, 143, 145, 146, 148,
    150, 152, 154, 156, 158, 160, 162, 164, 166, 168, 170, 172, 174, 176, 178, 180,
    182, 184, 187, 189, 191, 193, 195, 197, 200, 202, 204, 207, 209, 211, 213, 216,
    218, 221, 223, 225, 228, 230, 233, 235, 238, 240, 243, 245, 248, 250, 253, 255
]

# Manually calibrated
RED_ADJUSTMENT = 255
GREEN_ADJUSTMENT = 100
BLUE_ADJUSTMNET = 140

def modbus(msg: bytes) -> bytes:
    """
    Calculates the Modbus CRC16 checksum for a given message.

    Args:
        msg (bytes): The input message as a bytes object.

    Returns:
        bytes: The 2-byte CRC16 checksum in little-endian order.
    """
    crc = 0xFFFF
    for n in range(len(msg)):
        crc ^= msg[n]
        for i in range(8):
            if crc & 1:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return struct.pack("<H", crc)

def correct_color(color: RgbColor) -> RgbColor:
    """Apply gamma and hue channel color correction to a color"""
    # Apply gamma correction to each channel
    r = GAMMA_CORRECTION[min(255, max(0, color[0]))]
    g = GAMMA_CORRECTION[min(255, max(0, color[1]))]
    b = GAMMA_CORRECTION[min(255, max(0, color[2]))]

    # Hue
    r = r * RED_ADJUSTMENT // 255
    g = g * GREEN_ADJUSTMENT // 255
    b = b * BLUE_ADJUSTMNET // 255

    # Clamp values to 0-255
    r = min(255, max(0, r))
    g = min(255, max(0, g))
    b = min(255, max(0, b))

    return (r, g, b)
