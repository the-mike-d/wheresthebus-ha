"""Shared entity base for WheresTheBus."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WtbCoordinator


class WtbEntity(CoordinatorEntity[WtbCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: WtbCoordinator, child_id: str, key: str) -> None:
        super().__init__(coordinator)
        self._cid = child_id
        self._attr_unique_id = f"{child_id}_{key}"
        bus = (self.d or {}).get("bus_no") or self._child.get("busNo") or ""
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, child_id)},
            name=f"School bus {bus}".strip(),
            manufacturer="WheresTheBus (unofficial)",
            model=f"Route {self._child.get('routeNo') or bus}",
        )

    @property
    def _child(self) -> dict[str, Any]:
        for c in self.coordinator.children:
            if str(c.get("childId")) == self._cid:
                return c
        return {}

    @property
    def d(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get(self._cid) or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self.d)
