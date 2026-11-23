# Tuya Segments

Per-segment light control for Tuya RGBIC LED chains in Home Assistant.

Many Tuya RGBIC chains expose only one light entity, with per-segment colour hidden in a raw `draw_tool` datapoint (DP 59). This integration decodes that datapoint and creates one light entity per segment. It writes locally through [LocalTuya](https://github.com/xZetsubou/hass-localtuya) (`localtuya.set_dp`), so no cloud is involved.

Tested on: ALP235HA (10-segment RGBIC chain, protocol 3.3).

## Requirements

- Home Assistant with the [xZetsubou LocalTuya](https://github.com/xZetsubou/hass-localtuya) integration, and the chain already added to it.
- The chain's Tuya device ID, as shown in LocalTuya.

## Install

1. Copy `custom_components/tuya_segments/` to `<config>/custom_components/tuya_segments/`.
2. Add to `configuration.yaml`:

   ```yaml
   light:
     - platform: tuya_segments
       name: My RGBIC Chain        # entity names: "My RGBIC Chain Segment 01" …
       device_id: YOUR_TUYA_DEVICE_ID
       segments: 10                # optional, default 10
       # draw_dp: 59               # optional, DP holding draw_tool data
       # power_dp: 20              # optional, DP for the chain's main switch
   ```

3. Restart Home Assistant. The configuration check reports a newly copied custom integration as "not found" until the first restart. That is expected.

## Behaviour

- One `light` per segment, with on/off, HS colour and brightness.
- Writes within 150 ms are batched into one packet per colour, so a scene setting every segment sends one or two packets.
- Turning any segment on also switches the chain's power DP on.
- State is assumed (the device does not report per-segment state) and restored across restarts.
- No device is created: YAML platforms have no config entry, and Home Assistant 2027.8 forbids device info without one. A config flow is planned.

## DP 59 `draw_tool` format

Base64-encoded bytes:

```
01 | MM | 01 | HH HH | SS | VV | 00 00 | 80+N | (II II) × N
     │         │       │    │          │       └ 0-based segment index
     │         │       │    │          └ 0x80 + segment count
     │         │       │    └ value/brightness 0–100 (0 = segment off)
     │         │       └ saturation 0–100
     │         └ hue 0–360
     └ 01 = whole chain, 02 = listed segments
```

## Development

```bash
pip install pytest
pytest
```

`packet.py` has no Home Assistant imports, so the encoder tests run without Home Assistant installed.

## Uninstall

Remove the YAML block, delete the folder and restart.

## Licence

GPL-3.0. See [LICENSE](LICENSE).
