import asyncio
import base64
import contextlib
import random
import string
from typing import Optional

import aiohttp
import discord
from aiohttp.client import _WSRequestContextManager
from redbot.core import commands
from redbot.core.commands import Context

from .abc import MixinMeta


class WaifuDiffusionCommand(MixinMeta):
    async def _waifu_diffusion_join_queue(self) -> Optional[_WSRequestContextManager]:
        for x in range(25):
            session = await self.session.ws_connect(
                "wss://spaces.huggingface.tech/hakurei/waifu-diffusion-demo/queue/join"
            )
            first_message = await session.receive_json()
            if first_message["msg"] != "queue_full":
                return session
            await asyncio.sleep(1)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def waifudiffusion(self, ctx: Context, *, text: str):
        """
        Generate art using Waifu Diffusion.
        """
        if len(text) > 800:
            await ctx.reply("The text needs to be 800 characters or less.")
            return

        m = await ctx.reply("Attempting to join queue... This may take a while.")

        async with ctx.typing():
            session = await self._waifu_diffusion_join_queue()
            if session is None:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.reply("Failed to join queue. Please try again later.")
                return
            message_deleted = False
            async for msg in session:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = msg.json()

                    if data["msg"] == "send_data":
                        await session.send_json(
                            {
                                "fn_index": 2,
                                "data": [text],
                                "session_hash": "".join(
                                    random.choice(string.ascii_letters + string.digits)
                                    for _ in range(11)
                                ),
                            }
                        )
                    elif data["msg"] == "estimation":
                        seconds = int(data["rank_eta"])
                        minutes = int(seconds / 60)
                        new_message = (
                            (
                                f"Estimated wait time: {minutes} minute"
                                + ("s." if minutes != 1 else ".")
                            )
                            if minutes != 0
                            else (f"Estimated wait time: {seconds} seconds.")
                        )
                        if message_deleted:
                            m = await ctx.reply(new_message)
                            message_deleted = False
                        else:
                            await m.edit(content=new_message)
                        if not message_deleted:
                            if m.content != new_message:
                                try:
                                    await m.edit(content=new_message)
                                except discord.NotFound:
                                    message_deleted = True
                        if data["msg"] == "process_completed":
                            break

            if not message_deleted:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()

            images_b64 = data["output"]["data"][0]
            images = [base64.b64decode(x.split(",")[1]) for x in images_b64]

            await self.send_images(ctx, images)
