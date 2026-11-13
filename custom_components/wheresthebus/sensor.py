"""Sensors for WheresTheBus."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfLength, UnitOfTime
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import WtbEntity


async def async_setup_entry(hass, entry, async_add_entities: AddEntitiesCallback) -> None:
    coord = entry.runtime_data
    ents = []
    for cid in coord.data or {}:
        ents += [
            WtbDistance(coord, cid),
            WtbEta(coord, cid),
            WtbStatus(coord, cid),
            WtbScheduled(coord, cid),
            WtbHomeToStop(coord, cid),
        ]
    async_add_entities(ents)


class WtbDistance(WtbEntity, SensorEntity):
    _attr_name = "Distance to stop"
    _attr_icon = "mdi:map-marker-distance"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.MILES
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, c, cid):
        super().__init__(c, cid, "distance")

    @property
    def native_value(self):
        return self.d.get("distance") if self.d.get("tracking") else None


class WtbEta(WtbEntity, SensorEntity):
    _attr_name = "Minutes away"
    _attr_icon = "mdi:bus-clock"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_suggested_display_precision = 0

    def __init__(self, c, cid):
        super().__init__(c, cid, "eta")

    @property
    def native_value(self):
        return self.d.get("eta") if self.d.get("tracking") else None

    @property
    def extra_state_attributes(self):
        d = self.d
        return {"source": d.get("eta_source"), "learned_speed_mph": d.get("speed_mph")}


class WtbStatus(WtbEntity, SensorEntity):
    _attr_name = "Status"
    _attr_icon = "mdi:bus-school"

    def __init__(self, c, cid):
        super().__init__(c, cid, "status")

    @property
    def native_value(self):
        d = self.d
        if not self.coordinator.in_window():
            return "Outside bus hours"
        if d.get("passed_stop") and d.get("passed_at"):
            return f"Reached stop at {d['passed_at'].strftime('%-I:%M %p')}"
        return (d.get("notice") or d.get("eta_message") or ("Tracking" if d.get("tracking") else "Not running"))[:250]

    @property
    def extra_state_attributes(self):
        d = self.d
        keys = ("passed_stop", "passed_at", "status", "eta_message", "notice", "bus_no", "route_no", "stop_lat", "stop_lon", "school_lat", "school_lon")
        return {k: d.get(k) for k in keys}


class WtbScheduled(WtbEntity, SensorEntity):
    _attr_name = "Scheduled time"
    _attr_icon = "mdi:clock-outline"

    def __init__(self, c, cid):
        super().__init__(c, cid, "scheduled")

    @property
    def native_value(self):
        return self.d.get("scheduled") or self._child.get("busTime")


class WtbHomeToStop(WtbEntity, SensorEntity):
    """Straight-line distance from your home zone to the bus stop WheresTheBus has on file."""

    _attr_name = "Home to stop"
    _attr_icon = "mdi:home-import-outline"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.MILES
    _attr_suggested_display_precision = 2
    _attr_entity_registry_enabled_default = True

    def __init__(self, c, cid):
        super().__init__(c, cid, "home_to_stop")

    @property
    def native_value(self):
        return self.d.get("home_to_stop")
