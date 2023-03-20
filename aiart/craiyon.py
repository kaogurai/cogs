import base64
import contextlib

import discord
from redbot.core import commands
from redbot.core.commands import Context

from .abc import MixinMeta


class CraiyonCommand(MixinMeta):
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def craiyon(self, ctx: Context, *, text: str):
        """
        Generate art using Craiyon.

        The only argument is the text to generate the image from.
        """
        m = await ctx.reply("Generating art... This may take a while.")
        async with ctx.typing():
            json = {
                "prompt": text,
            }
            async with self.session.post(
                "https://backend.craiyon.com/generate", json=json
            ) as req:
                if req.status == 200:
                    json = await req.json()
                    if "images" not in json.keys():
                        with contextlib.suppress(discord.NotFound):
                            await m.delete()
                        await ctx.reply(
                            "Failed to generate art. Please try again later."
                        )
                        return
                else:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
                    await ctx.reply("Failed to generate art. Please try again later.")
                    return

            with contextlib.suppress(discord.NotFound):
                await m.delete()

        image_list = [base64.b64decode(image) for image in json["images"]]
        await self.send_images(ctx, image_list)
