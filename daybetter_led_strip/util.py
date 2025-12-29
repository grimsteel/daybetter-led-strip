import struct

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
