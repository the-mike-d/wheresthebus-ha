"""Minimal client for the WheresTheBus parent-app API (unofficial, reverse-engineered)."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from .const import API, BASE_URL, DEVICE_OS, DEVICE_TYPE

_LOGGER = logging.getLogger(__name__)

RES_OK = 0
RES_INVALID_SESSION = 9


class WtbError(Exception):
    """Generic API error."""


class WtbAuthError(WtbError):
    """Bad credentials or session that cannot be renewed."""


class WtbClient:
    """Talks to mdt.wheresthebus.com the same way the parent web app does."""

    def __init__(self, session: aiohttp.ClientSession, email: str, password: str, device_id: str) -> None:
        self._http = session
        self._email = email
        self._password = password
        self._device_id = device_id
        self.session_id: str | None = None
        self.base_path: str = BASE_URL
        self.first_name: str | None = None

    async def _post(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            async with asyncio.timeout(20):
                resp = await self._http.post(url, json=body, headers={"Accept": "application/json"})
                text = await resp.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise WtbError(f"connection error: {err}") from err
        if resp.status >= 500:
            raise WtbError(f"server error {resp.status}")
        try:
            data = json.loads(text)
        except ValueError as err:
            raise WtbError(f"bad response ({resp.status})") from err
        if not isinstance(data, dict):
            raise WtbError("unexpected response")
        return data

    async def login(self) -> None:
        data = await self._post(
            BASE_URL + API + "login",
            {
                "emailId": self._email,
                "password": self._password,
                "imeiNo": self._device_id,
                "deviceType": DEVICE_TYPE,
                "sso": 0,
                "deviceOS": DEVICE_OS,
            },
        )
        payload = data.get("payload") or {}
        if data.get("resCode") != RES_OK or not payload.get("sessionId"):
            raise WtbAuthError(data.get("mesgStr") or f"login failed (code {data.get('resCode')})")
        self.session_id = payload["sessionId"]
        base = payload.get("basePath")
        shard = payload.get("shardId") or data.get("shardId")
        if base and base.startswith("https://") and "wheresthebus.com" in base:
            self.base_path = base if base.endswith("/") else base + "/"
        elif shard:
            self.base_path = f"{BASE_URL}{shard}/"
        self.first_name = payload.get("firstName")
        _LOGGER.debug("WheresTheBus login ok, shard path %s", self.base_path)

    async def call(self, endpoint: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        """POST to a session endpoint, logging in again once if the session expired."""
        for attempt in (1, 2):
            if not self.session_id:
                await self.login()
            req = dict(body or {})
            req["sessionId"] = self.session_id
            data = await self._post(self.base_path + API + endpoint, req)
            code = data.get("resCode")
            if code == RES_OK:
                return data
            if code == RES_INVALID_SESSION or (code == 409 and attempt == 1):
                _LOGGER.debug("WheresTheBus session rejected (code %s), signing in again", code)
                self.session_id = None
                continue
            raise WtbError(data.get("mesgStr") or f"{endpoint} failed (code {code})")
        raise WtbAuthError("session could not be renewed")

    async def get_children(self) -> list[dict[str, Any]]:
        data = await self.call("getUserInfo")
        payload = data.get("payload") or {}
        return [c for c in (payload.get("childBuses") or []) if c.get("childId") is not None]

    async def get_rider(self, bus_no: str, child_id: Any, last_server_time: int = 0) -> dict[str, Any]:
        data = await self.call(
            "getRiderInfoEx", {"bid": bus_no, "chdId": child_id, "lastServerTime": last_server_time}
        )
        out = dict(data.get("payload") or {})
        out["serverTime"] = data.get("serverTime")
        return out
