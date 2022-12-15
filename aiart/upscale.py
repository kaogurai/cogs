import asyncio
import base64
import contextlib
import random
import string
from typing import Optional

import discord
from redbot.core import commands
from redbot.core.commands import Context

from .abc import MixinMeta


class UpscaleCommand(MixinMeta):
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def upscale(self, ctx: Context, link: Optional[str] = None):
        """
        Upscale an image.

        If no URL is provided, the bot the first image in the message.
        """
        if not link and not ctx.message.attachments:
            await ctx.send("Please provide an image to convert to text.")
            return

        if not link:
            link = str(ctx.message.attachments[0].url)

        m = await ctx.reply("Upscaling image... This may take a while.")

        async with ctx.typing():

            img = await self.get_image(link)
            if not img:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.reply("Failed to download image.")
                return

            mime_type = await self.get_image_mimetype(img)
            if not mime_type:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.reply(
                    "Failed to get image mimetype. Might be an invalid image."
                )
                return

            data = {
                "data": [
                    f"data:{mime_type};base64," + base64.b64encode(img).decode("utf-8"),
                ],
                "example_id": None,
                "session_hash": "".join(
                    random.choice(string.ascii_letters + string.digits)
                    for _ in range(11)
                ),
                "action": "predict",
            }
            async with self.session.post(
                "https://hf.space/embed/akhaliq/SwinIR/api/queue/push/", json=data
            ) as r:
                if r.status != 200:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
                    await ctx.reply(
                        "Something went wrong when trying to upscale the image."
                    )
                    return
                data = await r.json()
                image_hash = data["hash"]

            for x in range(300):  # Max 300 seconds
                body = {
                    "hash": image_hash,
                }
                async with self.session.post(
                    f"https://hf.space/embed/akhaliq/SwinIR/api/queue/status/",
                    json=body,
                ) as r:
                    if r.status != 200:
                        with contextlib.suppress(discord.NotFound):
                            await m.delete()
                        await ctx.reply(
                            "Something went wrong when trying to upscale the image."
                        )
                        return
                    data = await r.json()
                    if data["status"] == "COMPLETE":
                        break
                    await asyncio.sleep(1)
                if x == 299:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
                    await ctx.reply(
                        "Something went wrong when trying to upscale the image."
                    )
                    return

            image_base64 = data["data"]["data"][0].split(",")[1]
            image_bytes = base64.b64decode(image_base64)

            if ctx.guild:
                limit = ctx.guild.filesize_limit
            else:
                limit = 8000000

            if len(image_bytes) > limit:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.reply(
                    "The upscaled image is too large to send. Try in a server with a larger file size limit."
                )
                return

            await self.send_images(ctx, [image_bytes])
