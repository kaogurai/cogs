import asyncio
import random
import string
import uuid

import aiohttp
import discord
from redbot.core.commands import Context


class BlenderBotSession:
    def __init__(self, session: aiohttp.ClientSession, ctx: Context):
        self.ctx = ctx
        self.session = session
        self.channel = ctx.channel
        self.author = ctx.author
        self.bot = ctx.bot

    def _generate_user_id(self) -> str:
        return "".join(
            random.choice(string.ascii_letters + string.digits) for _ in range(32)
        )

    async def wait_for_message(self):
        def check(m):
            return m.author == self.author and m.channel == self.channel

        try:
            message = await self.bot.wait_for("message", timeout=30, check=check)
        except asyncio.TimeoutError:
            try:
                await self.channel.send("Session closed.")
            except discord.HTTPException:
                pass
            await self.close_session()
            return

        await self.send_message(message.content)
        await self.recieve_message()

    async def start_session(self) -> None:
        session = await self.session.ws_connect("wss://blenderbot.ai/chat_conn")
        self.ws_session = session

        await session.send_json(
            {
                "user_id": self._generate_user_id(),
                "source_id": "UNKNOWN",
                "request_arguments": {},
                "is_mobile": False,
                "time_zone": "America/New_York",
                "time_zone_UTC_offset": 240,
            }
        )
        await self.ws_session.receive_json()  # Just wait, this is the initial response
        await self.recieve_message()

    async def recieve_message(self) -> None:

        async with self.ctx.typing:
            resp = await self.ws_session.receive_json()

        try:
            await self.channel.send(resp["text"])
        except discord.HTTPException:
            await self.close_session()

        await self.wait_for_message()

    async def close_session(self) -> None:
        await self.ws_session.close()

    async def send_message(self, message: str) -> None:
        await self.ws_session.send_json(
            {
                "text": message,
                "flaggedMessageFeedback": False,
                "human_message_id": str(uuid.uuid4()),
            }
        )
