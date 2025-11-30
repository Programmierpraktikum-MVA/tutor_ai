import logging
from typing import Optional

from bot.handlers import Handlers

logger = logging.getLogger(__name__)


class Router:
    """Decides whether an incoming message is a command or a chat message."""

    def __init__(self, handlers: Handlers, command_prefix: str = "!"):
        self.handlers = handlers
        self.command_prefix = command_prefix

    async def route(self, message: str, room_id: str, sender: str) -> Optional[str]:
        text = message.strip()
        if not text:
            return None

        if text.startswith(self.command_prefix):
            return await self.handlers.handle_command(text, room_id, sender)

        return await self.handlers.handle_message(text, room_id, sender)
