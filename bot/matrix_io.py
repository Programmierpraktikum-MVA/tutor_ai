import logging
from pathlib import Path
from typing import Awaitable, Callable, Optional
from nio import AsyncClient, InviteEvent, RoomMessageText  # type: ignore[import]

from config import MatrixConfig

logger = logging.getLogger(__name__)


class MatrixBot:
    """Thin wrapper around matrix-nio for receiving and replying to messages."""

    def __init__(
        self,
        config: MatrixConfig,
        on_text_message: Callable[[str, str, str], Awaitable[Optional[str]]],
    ):
        self.config = config
        self.on_text_message = on_text_message
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
        self._has_seen_first_sync = False

    async def start(self) -> None:
        self.client.add_event_callback(self._message_callback, RoomMessageText)
        self.client.add_event_callback(self._invite_callback, InviteEvent)

        logger.info("Starting Matrix sync loop...")
        await self.client.sync_forever(timeout=30000, full_state=True)

    async def _invite_callback(self, room, event) -> None:
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

        return True

    async def send_message(self, room_id: str, body: str) -> None:
        await self.client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content={"msgtype": "m.text", "body": body},
        )

    async def close(self) -> None:
        await self.client.close()
