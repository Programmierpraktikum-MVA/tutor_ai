import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, Set

import aiohttp
import yaml
from nio import AsyncClient, InviteEvent, RoomMessageText
from nio.responses import ErrorResponse

from config import MatrixConfig

logger = logging.getLogger(__name__)


class MatrixBot:
    """Thin wrapper around matrix-nio for receiving and replying to messages."""

    def __init__(
        self,
        config: MatrixConfig,
        on_text_message: Callable[[str, str, str], Awaitable[Optional[str]]],
        allowed_rooms: Optional[Set[str]] = None,
        config_path: Optional[str] = None,
    ):
        self.config = config
        self.on_text_message = on_text_message
        self.allowed_rooms = allowed_rooms
        self.config_path = config_path
        self._refresh_lock = asyncio.Lock()
        self._last_refresh_attempt = 0.0
        self._refresh_cooldown_s = 30
        self._token_expiry_leeway_s = 30
        Path(self.config.store_path).mkdir(parents=True, exist_ok=True)

        self.client = AsyncClient(
            self.config.homeserver_url,
            self.config.user_id,
            device_id=self.config.device_id,
            store_path=self.config.store_path,
        )

        # Access token based authentication
        if self.config.access_token:
            self.client.access_token = self.config.access_token
        self.client.user_id = self.config.user_id
        self.client.add_response_callback(self._response_callback, ErrorResponse)
        self._has_seen_first_sync = False

    async def start(self) -> None:
        await self._ensure_logged_in()
        self.client.add_event_callback(self._message_callback, RoomMessageText)
        self.client.add_event_callback(self._invite_callback, InviteEvent)

        logger.info("Starting Matrix sync loop...")
        await self.client.sync_forever(timeout=30000, full_state=True)

    async def _invite_callback(self, room, event) -> None:
        if self.allowed_rooms and room.room_id not in self.allowed_rooms:
            logger.info(
                "Ignoring invite to room %s by %s (not in allowed list)",
                room.room_id,
                event.sender,
            )
            return

        logger.info("Invited to room %s by %s; joining", room.room_id, event.sender)
        await self.client.join(room.room_id)

    async def _message_callback(self, room, event) -> None:
        if not self._should_handle_event(room, event):
            return

        logger.info("Received message in %s from %s", room.room_id, event.sender)
        text = event.body.strip()

        try:
            response = await self.on_text_message(text, room.room_id, event.sender)
        except Exception:
            logger.exception("Failed to process message")
            response = "Entschuldigung, da ist etwas schiefgelaufen. Bitte versuche es erneut."

        if response:
            await self.send_message(room.room_id, response)

    def _should_handle_event(self, room, event) -> bool:
        if not self._has_seen_first_sync:
            # matrix-nio delivers backlog after startup; ignore that batch once
            self._has_seen_first_sync = True
            return False

        if event.sender == self.client.user_id:
            return False

        if room.encrypted:
            logger.warning("Skipping encrypted message in %s (unsupported)", room.room_id)
            return False

        if self.allowed_rooms and room.room_id not in self.allowed_rooms:
            logger.info(
                "Skipping message in room %s (not in allowed list)", room.room_id
            )
            return False

        return True

    async def send_message(self, room_id: str, body: str) -> None:
        await self.client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content={"msgtype": "m.text", "body": body},
        )

    async def close(self) -> None:
        await self.client.close()

    async def _ensure_logged_in(self) -> None:
        if self.config.access_token:
            self._restore_login()
        elif self.config.refresh_token:
            refreshed = await self._maybe_refresh_access_token("startup-no-access-token")
            if not refreshed:
                await self._login_with_password()
        else:
            await self._login_with_password()

        if self._token_expires_soon():
            await self._maybe_refresh_access_token("startup")

    def _restore_login(self) -> None:
        if not self.config.access_token:
            return
        self.client.restore_login(
            self.config.user_id, self.config.device_id, self.config.access_token
        )

    def _token_expires_soon(self) -> bool:
        if not self.config.token_expires_at:
            return False
        return time.time() >= (self.config.token_expires_at - self._token_expiry_leeway_s)

    def _get_matrix_password(self) -> Optional[str]:
        return os.environ.get("MATRIX_PASSWORD")

    async def _login_with_password(self) -> None:
        password = self._get_matrix_password()
        if not password:
            raise RuntimeError(
                "Matrix access_token is missing and MATRIX_PASSWORD is not set. "
                "Set MATRIX_PASSWORD for the first login or provide an access_token."
            )

        login_url = f"{self.config.homeserver_url.rstrip('/')}/_matrix/client/v3/login"
        payload: Dict[str, Any] = {
            "type": "m.login.password",
            "identifier": {"type": "m.id.user", "user": self.config.user_id},
            "password": password,
            "refresh_token": True,
        }
        if self.config.device_id:
            payload["device_id"] = self.config.device_id
            payload["initial_device_display_name"] = self.config.device_id

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(login_url, json=payload, timeout=15) as resp:
                    payload = await resp.json()
                    if resp.status != 200:
                        logger.error("Matrix login failed (%s): %s", resp.status, payload)
                        raise RuntimeError("Matrix login failed; see logs for details.")
        except Exception:
            logger.exception("Matrix login request failed")
            raise

        access_token = payload.get("access_token")
        if not access_token:
            raise RuntimeError("Matrix login response missing access_token.")

        refresh_token = payload.get("refresh_token")
        expires_in_ms = payload.get("expires_in_ms")
        token_expires_at = None
        if expires_in_ms is not None:
            token_expires_at = int(time.time() + (int(expires_in_ms) / 1000.0))

        device_id = payload.get("device_id") or self.config.device_id
        if not device_id:
            raise RuntimeError("Matrix login response missing device_id.")

        self.config.access_token = access_token
        self.config.refresh_token = refresh_token
        self.config.device_id = device_id
        self.config.token_expires_at = token_expires_at

        self.client.restore_login(self.config.user_id, device_id, access_token)

        self._persist_matrix_config(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expires_at": token_expires_at,
                "device_id": device_id,
            }
        )

        if not refresh_token:
            logger.warning(
                "Matrix login did not return refresh_token; access token may expire."
            )

    async def _response_callback(self, response: ErrorResponse) -> None:
        if not isinstance(response, ErrorResponse):
            return
        if response.status_code != "M_UNKNOWN_TOKEN":
            return
        await self._handle_unknown_token(response)

    async def _handle_unknown_token(self, response: ErrorResponse) -> None:
        reason = f"M_UNKNOWN_TOKEN soft_logout={response.soft_logout}"
        if await self._maybe_refresh_access_token(reason):
            return

        password = self._get_matrix_password()
        if not password:
            logger.warning(
                "Received M_UNKNOWN_TOKEN but no refresh_token or MATRIX_PASSWORD is configured "
                "(soft_logout=%s)",
                response.soft_logout,
            )
            return

        try:
            await self._login_with_password()
            logger.info("Re-logged in after M_UNKNOWN_TOKEN (soft_logout=%s)", response.soft_logout)
        except Exception:
            logger.exception(
                "Failed to re-login after M_UNKNOWN_TOKEN (soft_logout=%s)",
                response.soft_logout,
            )

    async def _maybe_refresh_access_token(self, reason: str) -> bool:
        if not self.config.refresh_token:
            logger.warning("Skipping token refresh (%s); no refresh_token configured.", reason)
            return False

        async with self._refresh_lock:
            now = time.time()
            if now - self._last_refresh_attempt < self._refresh_cooldown_s:
                logger.info(
                    "Skipping token refresh; last attempt %.1fs ago",
                    now - self._last_refresh_attempt,
                )
                return False
            self._last_refresh_attempt = now

            if await self._refresh_access_token():
                logger.info("Refreshed Matrix access token (%s).", reason)
                return True

            logger.error("Failed to refresh access token (%s).", reason)
            return False

    async def _discover_token_endpoint(self) -> Optional[str]:
        metadata_url = (
            f"{self.config.homeserver_url.rstrip('/')}/_matrix/client/v1/auth_metadata"
        )
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(metadata_url, timeout=10) as resp:
                    if resp.status != 200:
                        logger.warning(
                            "Failed to fetch auth metadata (status %s)", resp.status
                        )
                        return None
                    payload = await resp.json()
        except Exception:
            logger.exception("Failed to discover token endpoint")
            return None

        token_endpoint = payload.get("token_endpoint")
        if not token_endpoint:
            logger.warning("Auth metadata did not include token_endpoint")
            return None

        self.config.token_endpoint = token_endpoint
        self._persist_matrix_config({"token_endpoint": token_endpoint})
        return token_endpoint

    async def _refresh_access_token(self) -> bool:
        token_endpoint = self.config.token_endpoint
        if token_endpoint or self.config.client_id:
            if not token_endpoint:
                token_endpoint = await self._discover_token_endpoint()
            if token_endpoint and await self._refresh_access_token_oauth(token_endpoint):
                return True
            if token_endpoint:
                logger.warning("OAuth token refresh failed; trying /refresh endpoint.")

        return await self._refresh_access_token_matrix()

    async def _refresh_access_token_oauth(self, token_endpoint: str) -> bool:
        data: Dict[str, Any] = {
            "grant_type": "refresh_token",
            "refresh_token": self.config.refresh_token,
        }
        if self.config.client_id:
            data["client_id"] = self.config.client_id
        else:
            logger.warning("No OAuth client_id configured; refresh may fail.")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    token_endpoint,
                    data=data,
                    timeout=15,
                ) as resp:
                    if resp.status != 200:
                        logger.warning(
                            "Token refresh failed with status %s", resp.status
                        )
                        return False
                    payload = await resp.json()
        except Exception:
            logger.exception("Token refresh request failed")
            return False

        access_token = payload.get("access_token")
        if not access_token:
            logger.warning("Token refresh response missing access_token")
            return False

        refresh_token = payload.get("refresh_token") or self.config.refresh_token
        token_expires_at = self._parse_expiry(payload.get("expires_in"), payload.get("expires_in_ms"))

        self._apply_new_tokens(access_token, refresh_token, token_expires_at)
        return True

    async def _refresh_access_token_matrix(self) -> bool:
        if not self.config.refresh_token:
            logger.warning("No refresh_token configured for /refresh endpoint.")
            return False

        refresh_url = (
            f"{self.config.homeserver_url.rstrip('/')}/_matrix/client/v3/refresh"
        )
        payload: Dict[str, Any] = {"refresh_token": self.config.refresh_token}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(refresh_url, json=payload, timeout=15) as resp:
                    if resp.status != 200:
                        logger.warning(
                            "Token refresh failed with status %s", resp.status
                        )
                        return False
                    data = await resp.json()
        except Exception:
            logger.exception("Token refresh request failed")
            return False

        access_token = data.get("access_token")
        if not access_token:
            logger.warning("Token refresh response missing access_token")
            return False

        refresh_token = data.get("refresh_token") or self.config.refresh_token
        token_expires_at = self._parse_expiry(data.get("expires_in"), data.get("expires_in_ms"))

        self._apply_new_tokens(access_token, refresh_token, token_expires_at)
        return True

    def _parse_expiry(self, expires_in: Optional[Any], expires_in_ms: Optional[Any]) -> Optional[int]:
        if expires_in is None and expires_in_ms is not None:
            expires_in = int(expires_in_ms) / 1000
        if not expires_in:
            return None
        return int(time.time() + float(expires_in))

    def _apply_new_tokens(
        self, access_token: str, refresh_token: Optional[str], token_expires_at: Optional[int]
    ) -> None:
        self.config.access_token = access_token
        self.config.refresh_token = refresh_token
        self.config.token_expires_at = token_expires_at

        self.client.restore_login(
            self.config.user_id, self.config.device_id, access_token
        )

        self._persist_matrix_config(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expires_at": token_expires_at,
            }
        )

    def _persist_matrix_config(self, updates: Dict[str, Any]) -> None:
        if not self.config_path:
            return

        path = Path(self.config_path)
        try:
            with path.open("r") as handle:
                raw = yaml.safe_load(handle) or {}
        except FileNotFoundError:
            raw = {}

        matrix_cfg = raw.get("matrix")
        if matrix_cfg is None or not isinstance(matrix_cfg, dict):
            matrix_cfg = {}

        for key, value in updates.items():
            if value is None:
                matrix_cfg.pop(key, None)
                continue
            matrix_cfg[key] = value

        raw["matrix"] = matrix_cfg
        with path.open("w") as handle:
            yaml.safe_dump(raw, handle, sort_keys=False)
