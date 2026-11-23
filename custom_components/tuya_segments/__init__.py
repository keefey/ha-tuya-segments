"""Tuya Segments: per-segment lights for Tuya RGBIC chains, written via LocalTuya.

Decoded DP 59 (`draw_tool`) packet, confirmed on ALP235HA:

    01 | 02 | 01 | HH HH | SS | VV | 00 00 | 80+N | (II II) * N
         |         |       |    |            |       `- 0-based segment index
         |         |       |    |            `- 0x80 + segment count
         |         |       |    `- value/brightness 0-100
         |         |       `- saturation 0-100
         |         `- hue 0-360
         `- 01 = whole chain, 02 = selected segments
"""

DOMAIN = "tuya_segments"
