import asyncio
import contextlib
from typing import Optional

import discord
from aiohttp import FormData
from redbot.core import commands
from redbot.core.commands import Context

from .abc import MixinMeta


class CLIPCommand(MixinMeta):
    """
    Implements the Replicate API for methexis-inc/img2prompt.
    """

    @commands.command(aliases=["image2text", "img2txt", "image2prompt", "img2prompt"])
    @commands.bot_has_permissions(embed_links=True)
    async def clip(self, ctx: Context, url: Optional[str] = None):
        """
        Turn an image into a text.

        If no URL is provided, the bot the first image in the message.

        Only JPEG and PNG images are supported.
        """
        if url is None:
            if ctx.message.attachments:
                url = ctx.message.attachments[0].url
            else:
                await ctx.reply("You need to provide an image.")
                return

        m = await ctx.reply("Generating text... This may take a while.")
        async with ctx.typing():
            try:
                async with self.session.get(url) as req:
                    if req.status == 200:
                        image = await req.read()
                    else:
                        raise Exception
            except:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.reply("Failed to download image. Please try again later.")
                return

            data = FormData()
            data.add_field("file", image, filename=url.split("/")[-1].split("?")[0])

            async with self.session.post(
                "https://replicate.com/api/models/methexis-inc/img2prompt/files",
                data=data,
            ) as req:
                if req.status == 201:
                    json = await req.json()
                    image_uri = json["filename"]
                else:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
                    await ctx.reply(
                        "Failed to upload image. Keep in mind that only JPEG and PNG images are supported."
                    )
                    return

            json = {"inputs": {"image": image_uri}}

            async with self.session.post(
                "https://replicate.com/api/models/methexis-inc/img2prompt/versions/50adaf2d3ad20a6f911a8a9e3ccf777b263b8596fbd2c8fc26e8888f8a0edbb5/predictions",
                json=json,
            ) as req:
                if req.status == 201:
                    json = await req.json()
                    uuid = json["uuid"]
                else:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
                    await ctx.reply("Failed to generate text. Please try again later.")
                    return

            for x in range(24):
                if x == 23:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
                    await ctx.reply("Failed to generate text. Please try again later.")
                    return
                async with self.session.get(
                    f"https://replicate.com/api/models/methexis-inc/img2prompt/versions/50adaf2d3ad20a6f911a8a9e3ccf777b263b8596fbd2c8fc26e8888f8a0edbb5/predictions/{uuid}"
                ) as req:
                    if req.status == 200:
                        json = await req.json()
                        if json["prediction"]["status"] == "failed":
                            with contextlib.suppress(discord.NotFound):
                                await m.delete()
                            await ctx.reply(
                                "Failed to generate text. Please try again later."
                            )
                            return

                        if json["prediction"]["status"] == "succeeded":
                            break
                    else:
                        with contextlib.suppress(discord.NotFound):
                            await m.delete()
                        await ctx.reply(
                            "Failed to generate text. Please try again later."
                        )
                        return
                await asyncio.sleep(5)

            with contextlib.suppress(discord.NotFound):
                await m.delete()

            embed = discord.Embed(
                title="Image to Text",
                color=await ctx.embed_color(),
                url=url,
                description=json["prediction"]["output"],
            )

            await ctx.reply(embed=embed)
