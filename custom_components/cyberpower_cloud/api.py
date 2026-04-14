"""CyberPower PowerPanel Cloud internal API client."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import aiohttp

from .const import API_BASE_URL, HMAC_SECRET

_LOGGER = logging.getLogger(__name__)


class AuthError(Exception):
    """Authentication failure."""


class ApiError(Exception):
    """Generic API error."""


class CyberPowerCloudAPI:
    """Async client for CyberPower PowerPanel Cloud internal API."""

    def __init__(
        self, session: aiohttp.ClientSession, email: str, password: str
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._otp_key: str | None = None
        self._bearer_token: str | None = None
        self._devices: list[dict[str, Any]] = []

    @staticmethod
    def _encrypt_password(password: str) -> str:
        md5 = hashlib.md5(password.encode()).hexdigest().upper()
        hmac_hash = (
            hmac.new(HMAC_SECRET.encode(), password.encode(), hashlib.sha512)
            .hexdigest()
            .upper()
        )
        return md5 + hmac_hash

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self._bearer_token:
            h["Authorization"] = f"Bearer {self._bearer_token}"
        return h

    async def login(self) -> dict[str, Any]:
        """Login and obtain OTP key + bearer token."""
        _LOGGER.debug("Logging in as %s", self._email)
        payload = {
            "Account": self._email,
            "Password": self._encrypt_password(self._password),
            "LoginType": 10,
        }
        async with self._session.post(
            f"{API_BASE_URL}/LoginAccountWithDeviceInfo",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            _LOGGER.debug("Login response status: %d", resp.status)
            data = await resp.json(content_type=None)

        if not data.get("Flag"):
            msg = data.get("Message", "Login failed")
            _LOGGER.warning("Login failed for %s: %s", self._email, msg)
            raise AuthError(msg)

        self._otp_key = data["OtpKey"]
        self._bearer_token = data["token"]
        self._devices = data.get("DevicesInfor") or []

        _LOGGER.debug(
            "Login OK for %s, %d device(s): %s",
            self._email,
            len(self._devices),
            ", ".join(d.get("DeviceSN", "?") for d in self._devices),
        )
        return data

    @property
    def devices(self) -> list[dict[str, Any]]:
        return self._devices

    async def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST to API with auth. Re-login once on 401."""
        for attempt in range(2):
            _LOGGER.debug("API request: POST %s (attempt %d)", endpoint, attempt + 1)
            async with self._session.post(
                f"{API_BASE_URL}{endpoint}",
                data=json.dumps(payload, separators=(",", ":")),
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                _LOGGER.debug("API response: %s status=%d", endpoint, resp.status)
                data = await resp.json(content_type=None)

            if resp.status == 401 or (
                not data.get("result") and "expired" in str(data.get("errmsg", ""))
            ):
                if attempt == 0:
                    _LOGGER.debug("Token expired for %s, re-login", endpoint)
                    await self.login()
                    payload["otp"] = self._otp_key
                    continue
                _LOGGER.error("Re-login failed for %s", endpoint)
                raise AuthError("Re-login failed")

            if not data.get("result", True):
                errmsg = data.get("errmsg", {})
                body = (
                    errmsg.get("body", str(errmsg))
                    if isinstance(errmsg, dict)
                    else str(errmsg)
                )
                _LOGGER.warning("API error on %s: %s", endpoint, body)
                raise ApiError(f"{endpoint}: {body}")

            _LOGGER.debug("API success: %s", endpoint)
            return data
        raise ApiError(f"{endpoint}: max retries")

    async def get_device_status(self, sn: str) -> dict[str, Any]:
        """Get basic device status (battery, load, BHI)."""
        data = await self._post("/device/read/status", {"otp": self._otp_key, "sn": sn})
        status_list = data.get("msg", {}).get("device_status", [])
        if not status_list:
            raise ApiError("No device status returned")
        return status_list[0]

    async def get_status_log(self, dcode: int) -> dict[str, Any]:
        """Get latest status log entry (voltage, frequency, temp)."""
        now = int(time.time())
        data = await self._post(
            "/status/log",
            {
                "otp": self._otp_key,
                "dcode": dcode,
                "from": now - 900,
                "to": now,
            },
        )
        entries = data.get("msg", {}).get("body", [])
        if not entries:
            return {}
        return entries[0]  # most recent
