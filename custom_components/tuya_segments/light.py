"""Per-segment light entities for a Tuya RGBIC chain managed by LocalTuya.

Example configuration.yaml:

light:
  - platform: tuya_segments
    name: My RGBIC Chain
    device_id: YOUR_TUYA_DEVICE_ID
    segments: 10
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

import voluptuous as vol

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    PLATFORM_SCHEMA,
    ColorMode,
    LightEntity,
)
from homeassistant.const import CONF_DEVICE_ID, CONF_NAME, STATE_ON
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .packet import encode

_LOGGER = logging.getLogger(__name__)

CONF_SEGMENTS = "segments"
CONF_DRAW_DP = "draw_dp"
CONF_POWER_DP = "power_dp"

# Coalesce writes made within this window (e.g. a scene setting 10 segments) into
# one packet per colour.
FLUSH_DELAY = 0.15

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Optional(CONF_NAME, default="Tuya chain"): cv.string,
        vol.Optional(CONF_SEGMENTS, default=10): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=1000)
        ),
        vol.Optional(CONF_DRAW_DP, default=59): cv.positive_int,
        vol.Optional(CONF_POWER_DP, default=20): cv.positive_int,
    }
)


class Chain:
    """One physical chain; batches segment writes and sends them via LocalTuya."""

    def __init__(self, hass: HomeAssistant, device_id: str, draw_dp: int, power_dp: int) -> None:
        self.hass = hass
        self.device_id = device_id
        self.draw_dp = draw_dp
        self.power_dp = power_dp
        self._pending: dict[int, tuple[int, int, int]] = {}
        self._task: asyncio.Task | None = None

    def queue(self, index: int, hsv: tuple[int, int, int]) -> None:
        self._pending[index] = hsv
        if self._task is None:
            self._task = self.hass.async_create_task(self._flush_later())

    async def _flush_later(self) -> None:
        await asyncio.sleep(FLUSH_DELAY)
        pending, self._pending, self._task = self._pending, {}, None

        groups: dict[tuple[int, int, int], list[int]] = defaultdict(list)
        for idx, hsv in pending.items():
            groups[hsv].append(idx)

        if any(v > 0 for (_, _, v) in groups):
            await self._set_dp(self.power_dp, True)
        for (h, s, v), segs in groups.items():
            for packet in encode(segs, h, s, v):
                _LOGGER.debug("%s seg %s -> %s", self.device_id, segs, packet)
                await self._set_dp(self.draw_dp, packet)

    async def _set_dp(self, dp: int, value) -> None:
        try:
            await self.hass.services.async_call(
                "localtuya",
                "set_dp",
                {"device_id": self.device_id, "dp": dp, "value": value},
                blocking=True,
            )
        except Exception:  # noqa: BLE001 - surface any LocalTuya failure in the log
            _LOGGER.exception("localtuya.set_dp failed for %s dp %s", self.device_id, dp)


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
) -> None:
    chain = Chain(hass, config[CONF_DEVICE_ID], config[CONF_DRAW_DP], config[CONF_POWER_DP])
    name = config[CONF_NAME]
    async_add_entities(
        SegmentLight(chain, name, i) for i in range(config[CONF_SEGMENTS])
    )


class SegmentLight(LightEntity, RestoreEntity):
    """One segment. State is assumed: the device does not report per-segment state."""

    # YAML platform: no config entry, so no device (HA 2027.8 forbids device_info
    # without a config entry). Entity name carries the chain name instead.
    _attr_has_entity_name = False
    _attr_assumed_state = True
    _attr_should_poll = False
    _attr_color_mode = ColorMode.HS
    _attr_supported_color_modes = {ColorMode.HS}

    def __init__(self, chain: Chain, chain_name: str, index: int) -> None:
        self._chain = chain
        self._index = index
        self._attr_name = f"{chain_name} Segment {index + 1:02d}"
        self._attr_unique_id = f"{chain.device_id}_seg_{index + 1:02d}"
        self._attr_is_on = False
        self._attr_hs_color = (0.0, 100.0)
        self._attr_brightness = 255

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self._attr_is_on = last.state == STATE_ON
            if (hs := last.attributes.get(ATTR_HS_COLOR)) is not None:
                self._attr_hs_color = tuple(hs)
            if (bri := last.attributes.get(ATTR_BRIGHTNESS)) is not None:
                self._attr_brightness = bri

    def _hsv(self, on: bool) -> tuple[int, int, int]:
        h, s = self._attr_hs_color
        v = max(1, round(self._attr_brightness * 100 / 255)) if on else 0
        return int(round(h)), int(round(s)), v

    async def async_turn_on(self, **kwargs) -> None:
        if ATTR_HS_COLOR in kwargs:
            self._attr_hs_color = kwargs[ATTR_HS_COLOR]
        if ATTR_BRIGHTNESS in kwargs:
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]
        self._attr_is_on = True
        self._chain.queue(self._index, self._hsv(True))
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._attr_is_on = False
        self._chain.queue(self._index, self._hsv(False))
        self.async_write_ha_state()
