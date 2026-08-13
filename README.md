# Epson LabelWorks for Home Assistant

Custom Home Assistant integration that exposes an Epson LabelWorks LW-600P as a local printer. It generates the reverse-engineered Epson raster protocol directly and sends it over either USB or a Bluetooth Classic RFCOMM serial device.

## Features

- USB bulk transport, defaulting to Epson `04b8:0705`
- Bluetooth Classic serial transport through a paired `/dev/rfcomm*` device
- `text.epson_labelworks_print_label` entity for quick text printing
- `epson_labelworks.print_label` action for text or base64 PNG/JPEG printing
- tape width, automatic or fixed label length, font size, cut mode, density, and margin controls
- printer status, error, and detected tape width attributes
- all blocking USB, serial, rendering, and printing operations run outside Home Assistant's event loop

The implementation is currently specific to the LW-600P protocol. Other LabelWorks models may use different commands or Bluetooth profiles.

## Install

Copy `custom_components/epson_labelworks` into Home Assistant's `config/custom_components` directory, restart Home Assistant, then add **Epson LabelWorks** from **Settings > Devices & services**.

For HACS, add this repository as a custom integration repository.

## USB

Choose **USB** in the config flow. The defaults are:

- vendor ID: `0x04b8`
- product ID: `0x0705`
- interface: `0`

Home Assistant must have access to the USB device. Home Assistant Container deployments normally need the device passed through, for example:

```yaml
services:
  homeassistant:
    devices:
      - /dev/bus/usb:/dev/bus/usb
```

The host kernel printer driver may claim the interface; the integration attempts to detach it. Appropriate container permissions or udev rules are still required.

## Bluetooth

The integration's Bluetooth option is Bluetooth Classic serial, not BLE. Pair the printer on the Home Assistant host and bind its serial channel before setup:

```sh
bluetoothctl
pair AA:BB:CC:DD:EE:FF
trust AA:BB:CC:DD:EE:FF
quit
sudo rfcomm bind 0 AA:BB:CC:DD:EE:FF 1
```

Then configure `/dev/rfcomm0` and the printer's serial baud rate, default `115200`. Pass `/dev/rfcomm0` into the Home Assistant container if applicable.

Bluetooth support requires the printer/adapter to expose a bidirectional serial channel carrying the same protocol bytes. If the LW-600P advertises a proprietary or BLE-only service in your environment, an RFCOMM transport will not work without additional service discovery and framing research.

## Print Text

Writing a value to the integration's text entity prints a 12 mm label whose length is automatically sized to its text:

```yaml
action: text.set_value
target:
  entity_id: text.epson_lw_600p_print_label
data:
  value: "Front door batteries"
```

The entity is intentionally cleared after each print so the same text can be printed repeatedly.

## Print Action

```yaml
action: epson_labelworks.print_label
data:
  text: "Filter changed: {{ now().date() }}"
  tape_width_mm: 12
  length_mm: 60
  font_size: 24
  cut: after
  density: 0
  margin_mm: 1
```

When multiple printers are configured, select one with its config entry ID:

```yaml
action: epson_labelworks.print_label
data:
  config_entry_id: 01JEXAMPLE123
  text: "Pantry"
```

For images, provide `image_base64` instead of `text`. Exactly one must be supplied.
Text labels are automatically sized when `length_mm` is omitted. Image labels require `length_mm`.

## Development

Protocol and rendering tests do not require Home Assistant or printer hardware:

```sh
python -m pip install -e '.[test]'
pytest
```

Hardware validation is performed by the config flow, which opens the selected transport and requests a printer status frame.

## Protocol Source

This project reuses the protocol discovery from `epson-label-server`, based on:

- https://github.com/tyalie/RE-epson-label-printer
- https://github.com/oxplot/nospero
