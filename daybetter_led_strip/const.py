from bleak.uuids import normalize_uuid_16

# includes Device Name characteristic
SERVICE_GENERIC_ACCESS_PROFILE = normalize_uuid_16(0x1800)
# read
CHAR_DEVICE_NAME = normalize_uuid_16(0x2a00)

SERVICE_LED_CONTROL = normalize_uuid_16(0xe031)
# write
CHAR_LED_CONTROL = normalize_uuid_16(0xa031)
# "read", notify
CHAR_LED_STATUS = normalize_uuid_16(0xf031)

# Advertised service
SERVICE_DISCOVERY = normalize_uuid_16(0xc031)

# GATT command ID
COMMAND_BRIGHTNESS = 0x13
COMMAND_POWER = 0x11
COMMAND_COLOR = 0x15
