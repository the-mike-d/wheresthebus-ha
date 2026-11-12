"""Bus position as a device tracker."""
from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import WtbEntity


async def async_setup_entry(hass, entry, async_add_entities: AddEntitiesCallback) -> None:
    coord = entry.runtime_data
    async_add_entities(WtbBusTracker(coord, cid) for cid in coord.data or {})


class WtbBusTracker(WtbEntity, TrackerEntity):
    _attr_name = "Location"
    _attr_icon = "mdi:bus-school"

    def __init__(self, c, cid):
        super().__init__(c, cid, "location")

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self):
        return self.d.get("bus_lat") if self.d.get("tracking") else None

    @property
    def longitude(self):
        return self.d.get("bus_lon") if self.d.get("tracking") else None

    @property
    def location_accuracy(self) -> int:
        return 20
