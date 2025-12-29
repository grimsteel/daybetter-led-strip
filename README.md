# daybetter-led-strip

Python package to control Daybetter RGB LED strips over BLE. Uses [`bleak`](https://bleak.readthedocs.io/en/latest/index.html).

## Installation

`daybetter-led-strip` is on PyPI

```sh
$ pip install daybetter-led-strip
```

## Usage

The `DaybetterLedStrip` constructor only requires the device MAC address. After that, the actual underlying device and advertisment data can be updated any number of times using `.update_device`. If the device disconnects for any reason, it will not reconnect.

```python
device = await BleakScanner.find_device_by_filter(lambda _device, data: SERVICE_DISCOVERY in data.service_uuids)
    
led_strip = DaybetterLedStrip(device.address)
await led_strip.update_device(device, None)

# turn on
await led_strip.set_power(True)

await asyncio.sleep(1)

await led_strip.set_color((255, 0, 0))

await led_strip.set_power(False)
# Must be called when done using
await led_strip.disconnect()
```

A complete example program is provided in `examples/test.py`.

This package was created for use in Home Assistant, which may explain some of the API choices.
