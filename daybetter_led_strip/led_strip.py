import logging
from typing import cast, Callable

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.scanner import AdvertisementData
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from .const import CHAR_LED_CONTROL, CHAR_LED_STATUS, SERVICE_GENERIC_ACCESS_PROFILE, SERVICE_LED_CONTROL
from .util import modbus

_LOGGER = logging.Logger(__name__)

RgbColor = tuple[int, int, int]
Listener = Callable[[], None]

class DaybetterLedStrip:
    """Control a Daybetter RGB LED strip over Bluetooth Low Energy. Uses a BleakClient for the BLE connection"""

    address: str
    device: BLEDevice | None = None
    advertisment_data: AdvertisementData | None = None
    client: BleakClient | None = None

    # pending state changes sent via command
    pending_power: bool | None = None
    pending_color: RgbColor | None = None
    pending_brightness: int | None = None

    # current state
    power: bool | None = None
    color: RgbColor | None = None
    brightness: int | None = None

    listeners: list[Listener]

    def __init__(self, address: str):
        self.address = address

    async def update_device(self, device: BLEDevice | None, advertisment_data: AdvertisementData | None):
        """Update this client with a new BLEDevice and AdvertismentData from scanning. Will attempt to connect if applicable"""

        if device is not None and device.address != self.address:
            _LOGGER.warning("Updated device address %s does not match original address %s", device.address, self.address)

        was_connected = self.connected

        self.device = device
        self.advertisment_data = advertisment_data

        # attempt reconnect with new device
        if not was_connected and device is not None:
            await self.connect()

    async def connect(self):
        """Initialize the BleakClient"""

        if self.device is None:
            return

        self.client = BleakClient(
            self.device,
            disconnected_callback=self._on_disconnected,
            services=[SERVICE_GENERIC_ACCESS_PROFILE, SERVICE_LED_CONTROL]
        )
        await self.client.connect()
        await self.client.start_notify(CHAR_LED_STATUS, self._on_status_char_update)
        self._trigger_listeners()

    async def disconnect(self):
        """Manually disconnect the BleakClient"""

        if self.client is None:
            return

        # Clear event listeners and disconnect
        if self.client.is_connected:
            await self.client.stop_notify(CHAR_LED_STATUS)
            await self.client.disconnect()

        self.client = None
        self._trigger_listeners()

    async def _write_led_control(self, payload: bytes):
        """Write the given payload to the LED control characteristic.
        Prepends A0 and appends checksum to the payload.
        """
        if not self.connected:
            _LOGGER.warning("Cannot write characteristic: not connected to device")
            return

        full_payload = bytes([0xA0]) + payload
        full_payload += modbus(full_payload)  # checksum

        try:
            await cast(BleakClient, self.client).write_gatt_char(CHAR_LED_CONTROL, full_payload)
        except BleakError as e:
            _LOGGER.error("Failed to write characteristic: %s", e)

    async def set_color(self, new_color: RgbColor):
        """Attempt to configure the current color of the lights. Will not turn on if currently off"""

        r, g, b = new_color
        # 15 06 RR GG BB
        payload = bytes([0x15, 0x06, r & 0xFF, g & 0xFF, b & 0xFF])

        await self._write_led_control(payload)
        # will be committed to self.color when acked
        self.pending_color = new_color

    async def set_brightness(self, new_brightness: int):
        """Attempt to configure the brightness of the lights. Value should be between 0 and 100 (0x00 and 0x64)."""
        if not (0 <= new_brightness <= 100):
            _LOGGER.warning("Brightness value %d out of range (0-100)", new_brightness)
            return

        # 13 04 brightness
        payload = bytes([0x13, 0x04, new_brightness & 0xFF])
        await self._write_led_control(payload)
        # will be committed to self.brightness when acked
        self.pending_brightness = new_brightness

    async def set_power(self, on: bool):
        """Attempt to turn the lights on or off."""
        # 11 04 00 = off, 01 = on
        payload = bytes([0x11, 0x04, 0x01 if on else 0x00])
        await self._write_led_control(payload)
        # will be committed to self.power when acked
        self.pending_power = on

    async def _on_status_char_update(self, _char: BleakGATTCharacteristic, data: bytearray):
        # power change - sent when changed from IR remote
        # A1 10 11 [00|01] CRC
        if len(data) >= 4 and data[0] == 0xA1 and data[1] == 0x10 and data[2] == 0x11:
            self.power = data[3] == 0x01
            self._trigger_listeners()

        # ack - sent after we send a command - change state and trigger listeners
        # A1 XX XX 01 CRC
        if len(data) >= 4 and data[0] == 0xA1 and data[3] == 0x01:
            if data[1] == 0x11 and data[2] == 0x04:
                # Commit pending power
                if self.pending_power is not None:
                    self.power = self.pending_power
                    self.pending_power = None
                    self._trigger_listeners()
            elif data[1] == 0x13 and data[2] == 0x04:
                # Commit pending brightness
                if self.pending_brightness is not None:
                    self.brightness = self.pending_brightness
                    self.pending_brightness = None
                    self._trigger_listeners()
            elif data[1] == 0x15 and data[2] == 0x06:
                # Commit pending color
                if self.pending_color is not None:
                    self.color = self.pending_color
                    self.pending_color = None
                    self._trigger_listeners()

    def _on_disconnected(self, _old_client: BleakClient):
        # not async - can't do much here
        self.client = None
        self._trigger_listeners()

    def on_change(self, listener: Listener):
        """Add an event listener for device state change"""

        self.listeners.append(listener)

        return lambda: self.listeners.remove(listener)

    def _trigger_listeners(self):
        """Call all registered event listeners."""
        for listener in list(self.listeners):
            try:
                listener()
            except Exception as e:
                _LOGGER.error("Listener raised exception: %s", e)

    @property
    def connected(self) -> bool:
        return self.client is not None and self.client.is_connected

    @property
    def rssi(self) -> int | None:
        if self.advertisment_data is None:
            return None
        return self.advertisment_data.rssi
