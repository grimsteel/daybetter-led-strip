import logging
import traceback
from typing import cast, Callable

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.scanner import AdvertisementData
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from .const import CHAR_LED_CONTROL, CHAR_LED_STATUS, COMMAND_BRIGHTNESS, COMMAND_COLOR, COMMAND_EFFECT, COMMAND_POWER, SERVICE_GENERIC_ACCESS_PROFILE, SERVICE_LED_CONTROL, Effect
from .util import modbus

_LOGGER = logging.getLogger(__name__)

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
    pending_effect: Effect | None = None

    # current state
    power: bool | None = None
    color: RgbColor | None = None
    brightness: int | None = None
    effect: Effect | None = None

    listeners: list[Listener] = []

    def __init__(self, address: str):
        self.address = address

    async def update_device(self, device: BLEDevice | None, advertisment_data: AdvertisementData | None):
        """Update this client with a new BLEDevice and AdvertismentData from scanning. Will attempt to connect if applicable"""

        if device is not None and device.address != self.address:
            _LOGGER.warning("Updated device address %s does not match original address %s", device.address, self.address)

        was_connected = self.connected
        if self.connected:
            await self.disconnect()

        self.device = device
        self.advertisment_data = advertisment_data

        # attempt reconnect with new device
        if not was_connected and device is not None:
            await self.connect()

        self._trigger_listeners()

    async def connect(self):
        """Initialize the BleakClient"""

        if self.device is None:
            return

        try:
            self.client = await establish_connection(
                BleakClientWithServiceCache,
                self.device,
                self.device.name or "Unknown Device",
                disconnected_callback=self._on_disconnected,
                services=[SERVICE_GENERIC_ACCESS_PROFILE, SERVICE_LED_CONTROL],
            )
        except Exception:
            traceback.print_exc()
            self.client = None
        if self.client is not None:
            await self.client.start_notify(CHAR_LED_STATUS, self._on_status_char_update)

    async def disconnect(self):
        """Manually disconnect the BleakClient"""

        if self.client is None:
            return

        # Clear event listeners and disconnect
        if self.client.is_connected:
            await self.client.stop_notify(CHAR_LED_STATUS)
            await self.client.disconnect()

    async def _write_led_control(self, command: int, payload: bytes):
        """Write the given payload to the LED control characteristic.
        Prepends the header and appends checksum to the payload.
        """
        if not self.connected:
            _LOGGER.warning("Cannot write characteristic: not connected to device")
            return

        # leading byte + command + length + payload + checksum not included
        length = 3 + len(payload)
        full_payload = bytes([0xA0, command & 0xff, length & 0xff]) + payload
        full_payload += modbus(full_payload)  # checksum

        try:
            await cast(BleakClient, self.client).write_gatt_char(CHAR_LED_CONTROL, full_payload)
        except BleakError as e:
            _LOGGER.error("Failed to write characteristic: %s", e)

    async def set_color(self, new_color: RgbColor):
        """Attempt to configure the current color of the lights. Will not turn on if currently off"""

        r, g, b = new_color
        # RR GG BB
        payload = bytes([r & 0xFF, g & 0xFF, b & 0xFF])

        # will be committed to self.color when acked
        self.pending_color = new_color
        await self._write_led_control(COMMAND_COLOR, payload)

    async def set_brightness(self, new_brightness: int):
        """Attempt to configure the brightness of the lights. Value should be between 0 and 100 (0x00 and 0x64)."""
        if not (0 <= new_brightness <= 100):
            _LOGGER.warning("Brightness value %d out of range (0-100)", new_brightness)
            return

        # between 00 and 64
        payload = bytes([new_brightness & 0xFF])
        # will be committed to self.brightness when acked
        self.pending_brightness = new_brightness
        await self._write_led_control(COMMAND_BRIGHTNESS, payload)

    async def set_effect(self, effect: Effect):
        """Attempt to put the light into one of the preset effect modes."""
        payload = bytes([effect.value & 0xff])
        self.pending_effect = effect
        await self._write_led_control(COMMAND_EFFECT, payload)

    async def set_power(self, on: bool):
        """Attempt to turn the lights on or off."""
        # 00 = off, 01 = on
        payload = bytes([0x01 if on else 0x00])
        # will be committed to self.power when acked
        self.pending_power = on
        await self._write_led_control(COMMAND_POWER, payload)

    async def _on_status_char_update(self, _char: BleakGATTCharacteristic, data: bytearray):
        print(data)

        # power change - sent when changed from IR remote
        # A1 10 11 [00|01] CRC
        if len(data) >= 4 and data[0] == 0xA1 and data[1] == 0x10 and data[2] == 0x11:
            self.power = data[3] == 0x01
            self._trigger_listeners()

        # ack - sent after we send a command - change state and trigger listeners
        # A1 XX 04 01 CRC
        if len(data) >= 4 and data[0] == 0xA1 and data[3] == 0x01:
            if data[1] == COMMAND_POWER:
                # Commit pending power
                if self.pending_power is not None:
                    self.power = self.pending_power
                    self.pending_power = None
                    self._trigger_listeners()
            elif data[1] == COMMAND_EFFECT:
                # Commit pending effect
                if self.pending_effect is not None:
                    self.effect = self.pending_effect
                    self.pending_effect = None
                    # effect clears color
                    self.color = None
                    self._trigger_listeners()
            elif data[1] == COMMAND_BRIGHTNESS:
                # Commit pending brightness
                if self.pending_brightness is not None:
                    self.brightness = self.pending_brightness
                    self.pending_brightness = None
                    self._trigger_listeners()
            elif data[1] == COMMAND_COLOR:
                # Commit pending color
                if self.pending_color is not None:
                    self.color = self.pending_color
                    self.pending_color = None
                    # color clears effect
                    self.effect = None
                    self._trigger_listeners()

    def _on_disconnected(self, _old_client: BleakClient):
        _LOGGER.warning("Device disconnected")

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
