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
