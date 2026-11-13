"""Binary sensors for WheresTheBus."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ALERT_MILES,
    CONF_BUFFER_MIN,
    CONF_DRIVE_MIN,
    DEFAULT_ALERT_MILES,
    DEFAULT_BUFFER_MIN,
    DEFAULT_DRIVE_MIN,
)
from .entity import WtbEntity


async def async_setup_entry(hass, entry, async_add_entities: AddEntitiesCallback) -> None:
    coord = entry.runtime_data
    ents = []
    for cid in coord.data or {}:
        ents += [WtbTimeToLeave(coord, cid), WtbTracking(coord, cid)]
    async_add_entities(ents)


class WtbTimeToLeave(WtbEntity, BinarySensorEntity):
    """On when the bus will reach the stop within travel time + buffer, or is within the alert distance."""

    _attr_name = "Time to leave"
    _attr_icon = "mdi:car-clock"

    def __init__(self, c, cid):
        super().__init__(c, cid, "time_to_leave")

    @property
    def _lead(self) -> int:
        o = self.coordinator.entry.options
        return int(o.get(CONF_DRIVE_MIN, DEFAULT_DRIVE_MIN)) + int(o.get(CONF_BUFFER_MIN, DEFAULT_BUFFER_MIN))

    @property
    def is_on(self) -> bool:
        d = self.d
        if not d.get("tracking") or d.get("passed_stop"):
            return False
        miles = float(self.coordinator.entry.options.get(CONF_ALERT_MILES, DEFAULT_ALERT_MILES) or 0)
        by_time = d.get("eta") is not None and d["eta"] <= self._lead
        by_distance = miles > 0 and d.get("distance") is not None and d["distance"] <= miles
        return bool(by_time or by_distance)

    @property
    def extra_state_attributes(self):
        o = self.coordinator.entry.options
        return {
            "lead_minutes": self._lead,
            "drive_minutes": o.get(CONF_DRIVE_MIN, DEFAULT_DRIVE_MIN),
            "buffer_minutes": o.get(CONF_BUFFER_MIN, DEFAULT_BUFFER_MIN),
            "alert_miles": o.get(CONF_ALERT_MILES, DEFAULT_ALERT_MILES),
        }


class WtbTracking(WtbEntity, BinarySensorEntity):
    _attr_name = "Bus en route"
    _attr_icon = "mdi:bus-marker"

    def __init__(self, c, cid):
        super().__init__(c, cid, "tracking")

    @property
    def is_on(self) -> bool:
        return bool(self.d.get("tracking"))
