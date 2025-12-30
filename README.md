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
from bleak import BleakScanner
from daybetter_led_strip import DaybetterLedStrip
from daybetter_led_strip.const import SERVICE_DISCOVERY

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

This package was created [for use in Home Assistant](https://github.com/grimsteel/homeassistant-daybetter-led-strip), which may explain some of the API choices.

## Protocol

Communication with the LED strip is done over BLE.

The light strip exposes two services: the generic access profile w/ the device name, and a custom "LED control service" (`0xe031`).

During discovery, the device also advertises itself with a third service (`0xc031`) for identification.

The LED control service has a read characteristic (`0xf031`) and a write characteristic (`0xa031`). As far as I can tell, the read characteristic cannot actually be read directly. Rather, if notifications are enabled on this service, the device will push updates about its state at various times.

### Write Data Format

Commands written to the write characteristic have the following format. 

1. The byte `0xA0` (referred to in the app source code as "APP_TO_DEVICE")
2. The command ID. (1 byte)
3. The length of the entire message, not including the checksum. (1 byte) `= len(payload) + 3`
4. The payload for this command
5. The little-endian CRC16 MODBUS checksum of the rest of the message.

### Commands

| Command         | ID     | Payload Description                                                                                  |
|-----------------|--------|-----------------------------------------------------------------------------------------------------|
| **Get status**  | `0x10` | `0x00`<br>Results in status payload below being sent on notify                                      |
| **Set power**   | `0x11` | `0x01` (on) or `0x00` (off)                                                                         |
| **Show effect** | `0x12` | One of the effect bytes listed below                                                                |
| **Set brightness** | `0x13` | A byte representing the brightness, from 0 (`0x00`) to 100 (`0x64`). Brightness 0 still has the LEDs slightly on |
| **Set color**   | `0x15` | 3 bytes, in RGB order                                                                               |

Example command (set to red): `A0 15 06 FF 00 00 25 C0`

### Notify/read data format

The payloads received over notify have a similar structure as the write commands:

1. The byte `0xA1` ("DEVICE_TO_APP")
2. Command ID
3. Length of entire message excluding checksum
4. Payload 
5. LE Checksum

### Received "commands"

When any of the above write commands are written to the characteristic successfully, the device responds with a message with the same command ID and `0x01` for the payload.

For instance, the above color command would result in `A1 15 04 01 F1 1C`

When the strip is turned on/off from the IR remote, a message with command ID `0x10` and the payload `00 01 01 64 32 32 ff 31 2d f0 00 00 00 00` (off) or `01 01 01 64 32 32 ff 31 2d f0 00 00 00 00`. The first byte indicates the on/off status, but I don't know what the rest means. It seems unrelated to the color of the light.

Running the "get status" command also results in this being sent.

### Effects

> Note: the brightness can be changed during the following effects. Lower brightnesses result in blinking happening faster, likely because there is a smaller range of brightnesses to interpolate between.

RGB: just red/green/blue
All preset colors: red/green/blue/yellow/teal/purple/white

`0x02..0x08`: show preset colors
`0x09`: switch RGB abruptly, no transition
`0x0A`: switch all preset colors
`0x0B`: fade between colors quickly
`0x0C`: fade between colors slowly
`0x0D`..`0x13`: blink individual preset colors
`0x14`: fade red/green
`0x15`: fade red/blue
`0x16`: fade green/blue
`0x17`: flash all preset colors
`0x18`..`0x1E`: flash individual preset colors
`0x1F`: strobe RGB
`0x20`: strobe all colors
