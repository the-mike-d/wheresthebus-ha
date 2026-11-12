"""Polling coordinator for WheresTheBus."""
from __future__ import annotations

from collections import deque
from datetime import datetime, time, timedelta
import logging
import math
import re
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import WtbAuthError, WtbClient, WtbError
from .const import (
    CONF_AM_ENABLED,
    CONF_AM_WINDOW,
    CONF_HOME_ZONE,
    DEFAULT_HOME_ZONE,
    CONF_PM_ENABLED,
    DEFAULT_AM_ENABLED,
    DEFAULT_PM_ENABLED,
    CONF_PM_WINDOW,
    CONF_WEEKDAYS_ONLY,
    DEFAULT_AM_WINDOW,
    DEFAULT_PM_WINDOW,
    DOMAIN,
    FALLBACK_MPH,
    FAST_INTERVAL,
    IDLE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)
_WIN = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*$")


def parse_window(text: str) -> tuple[time, time] | None:
    m = _WIN.match(text or "")
    if not m:
        return None
    a, b, c, d = (int(x) for x in m.groups())
    return time(a, b), time(c, d)


def miles_between(a: tuple[float, float] | None, b: tuple[float, float] | None) -> float | None:
    """Straight-line distance in miles."""
    if not a or not b or None in a or None in b:
        return None
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def _num(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f


class WtbCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches bus data every 15 s inside the bus windows, nothing outside them."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: WtbClient) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=FAST_INTERVAL), config_entry=entry
        )
        self.client = client
        self.entry = entry
        self.children: list[dict[str, Any]] = []
        self._children_at: datetime | None = None
        self._hist: dict[str, deque] = {}
        self._speed: dict[str, float] = {}
        self._server_time: dict[str, int] = {}

    # ---- schedule -------------------------------------------------------
    def in_window(self, now: datetime | None = None) -> bool:
        now = now or dt_util.now()
        opts = self.entry.options
        if opts.get(CONF_WEEKDAYS_ONLY, True) and now.weekday() >= 5:
            return False
        t = now.time()
        windows = (
            (CONF_AM_ENABLED, DEFAULT_AM_ENABLED, CONF_AM_WINDOW, DEFAULT_AM_WINDOW),
            (CONF_PM_ENABLED, DEFAULT_PM_ENABLED, CONF_PM_WINDOW, DEFAULT_PM_WINDOW),
        )
        for en_key, en_default, key, default in windows:
            if not opts.get(en_key, en_default):
                continue
            w = parse_window(opts.get(key, default))
            if w and w[0] <= t <= w[1]:
                return True
        return False

    def home_coords(self) -> tuple[float, float] | None:
        """Home location from the chosen zone (Settings > Areas & zones), not from WheresTheBus."""
        st = self.hass.states.get(self.entry.options.get(CONF_HOME_ZONE, DEFAULT_HOME_ZONE))
        if not st:
            return None
        lat, lon = _num(st.attributes.get("latitude")), _num(st.attributes.get("longitude"))
        return (lat, lon) if lat is not None and lon is not None else None

    # ---- polling --------------------------------------------------------
    async def _async_update_data(self) -> dict[str, Any]:
        active = self.in_window()
        self.update_interval = timedelta(seconds=FAST_INTERVAL if active else IDLE_INTERVAL)
        try:
            now = dt_util.utcnow()
            if not self.children or not self._children_at or now - self._children_at > timedelta(hours=6):
                self.children = await self.client.get_children()
                self._children_at = now
            if not active:
                # Outside bus windows: keep the last values but mark tracking off; no API traffic.
                old = dict(self.data or {})
                for cid in old:
                    old[cid] = {**old[cid], "tracking": False}
                if not old:
                    old = {str(c["childId"]): self._empty(c) for c in self.children}
                return old
            out: dict[str, Any] = {}
            for child in self.children:
                cid = str(child["childId"])
                bus = str(child.get("busNo") or "")
                if not bus:
                    out[cid] = self._empty(child)
                    continue
                raw = await self.client.get_rider(bus, child["childId"], self._server_time.get(cid, 0))
                if raw.get("serverTime"):
                    self._server_time[cid] = int(raw["serverTime"])
                out[cid] = self._compute(cid, child, raw)
            return out
        except WtbAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except WtbError as err:
            raise UpdateFailed(str(err)) from err

    def _empty(self, child: dict[str, Any]) -> dict[str, Any]:
        return {"child": child, "tracking": False, "bus_lat": None, "bus_lon": None, "distance": None, "eta": None}

    def _compute(self, cid: str, child: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
        lat, lon, dist = _num(raw.get("busLat")), _num(raw.get("busLon")), _num(raw.get("dist"))
        if raw.get("isDistKm") and dist is not None:
            dist = dist * 0.621371
        has_bus = bool(lat and lon) and dist is not None
        now = dt_util.utcnow().timestamp()

        # Learn the bus's approach speed from successive distances.
        hist = self._hist.setdefault(cid, deque(maxlen=40))
        if has_bus:
            if hist and dist > hist[-1][1] + 0.3:
                hist.clear()  # bus moved away / new trip: start over
                self._speed.pop(cid, None)
            hist.append((now, dist))
            while len(hist) > 2 and now - hist[0][0] > 240:
                hist.popleft()
            t0, d0 = hist[0]
            if now - t0 >= 45 and d0 - dist > 0.05:
                mph = (d0 - dist) / ((now - t0) / 3600)
                mph = max(5.0, min(45.0, mph))
                prev = self._speed.get(cid)
                self._speed[cid] = mph if prev is None else prev * 0.6 + mph * 0.4

        eta = None
        eta_src = None
        m = re.search(r"(\d+)\s*min", str(raw.get("etaMsg") or ""), re.I)
        if m:
            eta, eta_src = float(m.group(1)), "wheresthebus"
        elif has_bus:
            speed = self._speed.get(cid)
            eta = round(dist / (speed or FALLBACK_MPH) * 60, 1)
            eta_src = "learned speed" if speed else "estimate"

        return {
            "child": child,
            "tracking": has_bus,
            "bus_lat": lat,
            "bus_lon": lon,
            "distance": round(dist, 2) if dist is not None else None,
            "eta": eta,
            "eta_source": eta_src,
            "speed_mph": round(self._speed[cid], 1) if cid in self._speed else None,
            "stop_lat": _num(raw.get("stpLat")),
            "stop_lon": _num(raw.get("stpLon")),
            "home_to_stop": (
                round(m, 2)
                if (m := miles_between(self.home_coords(), (_num(raw.get("stpLat")), _num(raw.get("stpLon")))))
                is not None
                else None
            ),
            "school_lat": _num(raw.get("schLat")),
            "school_lon": _num(raw.get("schLon")),
            "status": raw.get("stsMsg") or None,
            "eta_message": raw.get("etaMsg") or None,
            "notice": raw.get("noMsg") or raw.get("IndBsMsg") or raw.get("districtBanner") or None,
            "scheduled": child.get("busTime"),
            "bus_no": child.get("busNo"),
            "route_no": child.get("routeNo"),
        }
