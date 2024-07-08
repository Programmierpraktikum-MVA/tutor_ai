import asyncio
import aiohttp
from nio import AsyncClient, LoginResponse, RoomMessageText
from config import Config

class MatrixBot:
    def __init__(self, config_path):
        self.config = Config(config_path)
        self.client = AsyncClient(self.config.homeserver_url, self.config.user_id)
        self.first_sync = True  # Flag to mark the first sync

    async def login(self):
        response = await self.client.login(self.config.user_password)
        if isinstance(response, LoginResponse):
            print("Login successful")
            return True
        else:
            print(f"Failed to log in: {response}")
            return False

    async def start_listening(self):
        # Use sync_forever with a custom loop to handle the first sync token
        async def sync_callback():
            await self.client.sync(timeout=30000, full_state=True)  # Perform a full state sync initially
            self.first_sync = False  # After the first sync, unset the flag
            await self.client.sync_forever(timeout=30000)

        self.client.add_event_callback(self.message_callback, RoomMessageText)
        await sync_callback()

    async def message_callback(self, room, event):
        if self.first_sync:
            return

        if room.encrypted:
            try:
                decryption_result = await self.client.decrypt_event(event)
                event = decryption_result.plaintext_event
            except Exception as e:
                print(f"Error decrypting event: {e}")
                return

        if room.room_id == "!umdPEgiAxrESYgzAnj:matrix.tu-berlin.de":
            if event.sender != self.client.user_id and event.body.startswith("@TutorAI"):
                response = await self.query_backend(event.body)
                await self.client.room_send(
                    room_id=room.room_id,
                    message_type="m.room.message",
                    content={"msgtype": "m.text", "body": response["answer"]}
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
