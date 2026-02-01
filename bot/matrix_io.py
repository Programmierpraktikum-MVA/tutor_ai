import asyncio
import logging
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
        Path(self.config.store_path).mkdir(parents=True, exist_ok=True)

        self.client = AsyncClient(
            self.config.homeserver_url,
            self.config.user_id,
            device_id=self.config.device_id,
            store_path=self.config.store_path,
        )

        # Access token based authentication
        self.client.access_token = self.config.access_token
        self.client.user_id = self.config.user_id
        self.client.add_response_callback(self._response_callback, ErrorResponse)
        self._has_seen_first_sync = False

    async def start(self) -> None:
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

    async def _response_callback(self, response: ErrorResponse) -> None:
        if not isinstance(response, ErrorResponse):
            return
        if response.status_code != "M_UNKNOWN_TOKEN":
            return
        await self._handle_unknown_token(response)

    async def _handle_unknown_token(self, response: ErrorResponse) -> None:
        if not self.config.refresh_token:
            logger.warning(
                "Received M_UNKNOWN_TOKEN but no refresh_token is configured "
                "(soft_logout=%s)",
                response.soft_logout,
            )
            return

        async with self._refresh_lock:
            now = time.time()
            if now - self._last_refresh_attempt < self._refresh_cooldown_s:
                logger.info("Skipping token refresh; last attempt %.1fs ago", now - self._last_refresh_attempt)
                return
            self._last_refresh_attempt = now

            if await self._refresh_access_token():
                logger.info("Refreshed Matrix access token.")
            else:
                logger.error(
                    "Failed to refresh access token after M_UNKNOWN_TOKEN "
                    "(soft_logout=%s)",
                    response.soft_logout,
                )

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
        if not token_endpoint:
            token_endpoint = await self._discover_token_endpoint()
        if not token_endpoint:
            logger.error("No token endpoint available for OAuth refresh")
            return False

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
        expires_in = payload.get("expires_in")
        if expires_in is None and payload.get("expires_in_ms") is not None:
            expires_in = int(payload["expires_in_ms"]) / 1000

        token_expires_at = None
        if expires_in:
            token_expires_at = int(time.time() + float(expires_in))

        self.config.access_token = access_token
        self.config.refresh_token = refresh_token
        if token_expires_at:
            self.config.token_expires_at = token_expires_at

        self.client.access_token = access_token

        self._persist_matrix_config(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expires_at": token_expires_at,
            }
        )
        return True

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
            if value is not None:
                matrix_cfg[key] = value

        raw["matrix"] = matrix_cfg
        with path.open("w") as handle:
            yaml.safe_dump(raw, handle, sort_keys=False)
