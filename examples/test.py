import asyncio
import logging

from bleak import BleakScanner

from daybetter_led_strip import DaybetterLedStrip
from daybetter_led_strip.const import SERVICE_DISCOVERY

_LOGGER = logging.getLogger(__name__)

async def run():
    logging.basicConfig(level = logging.INFO)

    # Search for BLE devices with our char
    device = await BleakScanner.find_device_by_filter(lambda _device, data: SERVICE_DISCOVERY in data.service_uuids)
    if device is None:
        _LOGGER.error("Could not find device with service %s", SERVICE_DISCOVERY)
        return

    led_strip = DaybetterLedStrip(device.address)
    _LOGGER.info("Found device with address %s", device.address)

    def on_change():
        _LOGGER.info("State: %s | Color: %s | Brightness: %s | Connected: %s | RSSI: %s", led_strip.power, led_strip.color, led_strip.brightness, led_strip.connected, led_strip.rssi)

    led_strip.on_change(on_change)

    await led_strip.update_device(device, None)

    # turn on
    await led_strip.set_power(True)

    await asyncio.sleep(1)

    await led_strip.set_color((255, 0, 0))

    await asyncio.sleep(0.5)

    await led_strip.set_color((0, 255, 0))

    await asyncio.sleep(0.5)

    await led_strip.set_color((0, 0, 255))

    await asyncio.sleep(0.5)

    await led_strip.set_brightness(10)

    await asyncio.sleep(1)

    await led_strip.set_power(False)
    # Must be called when done using
    await led_strip.disconnect()

asyncio.run(run())
