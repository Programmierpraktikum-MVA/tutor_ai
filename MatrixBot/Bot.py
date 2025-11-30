import asyncio
import aiohttp
from nio import AsyncClient, LoginResponse, RoomMessageText, InviteEvent
from config import Config

class MatrixBot:
    def __init__(self, config_path):
        self.config = Config(config_path)

        # Init Matrix client WITHOUT password login
        self.client = AsyncClient(
            self.config.homeserver_url,
            self.config.user_id,
            device_id="BOTDEVICE",
            store_path="./store"  # needed for sync token
        )

        # Use access token instead of login()
        self.client.access_token = self.config.access_token
        self.client.user_id = self.config.user_id

        self.first_sync = True  # Flag to mark the first sync

    async def login(self):

        # With access token we do not login again
        print("Using access token authentication")
        return True

    async def start_listening(self):
        # Register callback for new messages
        self.client.add_event_callback(self.message_callback, RoomMessageText)

        # Auto-join rooms when invited
        self.client.add_event_callback(self.invite_callback, InviteEvent)


        print("Starting sync loop...")
        await self.client.sync_forever(timeout=30000, full_state=True)

    async def invite_callback(self, room, event):
        print(f"Got invite to room {room.room_id}, joining...")
        await self.client.join(room.room_id)


    async def message_callback(self, room, event):
        # Ignore first full sync events
        if self.first_sync:
            self.first_sync = False
            return

        # Ignore our own messages
        if event.sender == self.client.user_id:
            return

        # Ignore encrypted rooms (we do not support E2E)
        if room.encrypted:
            print("Skipping encrypted message (bot cannot decrypt).")
            return

        print("Received message:", repr(event.body))

        # Only respond to messages starting with #TutorAI
        if event.body.startswith("#TutorAI"):
            print(f"Received question: {event.body}")

            response = await self.query_backend(event.body)

            answer = response.get("answer", "Kein Backend verfügbar.")

            await self.client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": answer
                }
            )

    async def query_backend(self, question):
        url = 'http://localhost:5000/ask'
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={"question": question}) as resp:
                return await resp.json()

    async def close(self):
        await self.client.close()


async def main():
    bot = MatrixBot("config.yaml")
    if await bot.login():
        await bot.start_listening()
    await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
