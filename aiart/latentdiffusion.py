import asyncio
import base64
import contextlib
import random
import string

import discord
from redbot.core import commands
from redbot.core.commands import Context

from .abc import MixinMeta


class LatentDiffusionCommand(MixinMeta):
    """
    Implements the Hugging Face Latent Diffusion API.
    """

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def latentdiffusion(self, ctx: Context, *, text: str):
        """
        Generate art using Latent Diffusion.
        """
        if len(text) > 250:
            await ctx.reply("The text needs to be 250 characters or less.")
            return

        m = await ctx.reply("Generating art... This may take a while.")

        async with ctx.typing():
            data = {
                "data": [
                    text,
                    50,
                    256,
                    256,
                    1,
                    5,
                ],
                "cleared": False,
                "example_id": None,
                "session_hash": "".join(
                    random.choice(string.ascii_letters + string.digits) for _ in range(11)
                ),
                "action": "predict",
            }
            async with self.session.post(
                "https://hf.space/embed/multimodalart/latentdiffusion/api/queue/push/",
                json=data,
            ) as req:
                if req.status != 200:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
                    await ctx.reply("Failed to generate art. Please try again later.")
                    return

                json = await req.json()

            data = {
                "hash": json["hash"],
            }

            for x in range(120):
                if x == 119:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
                    await ctx.reply("Failed to generate art. Please try again later.")
                    return

                async with self.session.post(
                    "https://hf.space/embed/multimodalart/latentdiffusion/api/queue/status/",
                    json=data,
                ) as req:
                    if req.status != 200:
                        with contextlib.suppress(discord.NotFound):
                            await m.delete()
                        await ctx.reply("Failed to generate art. Please try again later.")
                        return

                    json = await req.json()

                    if json["status"] == "COMPLETE":
                        break

                await asyncio.sleep(5)

            image_base64 = json["data"]["data"][0]
            if not image_base64 and "NSFW" in json["data"]["data"][-1]:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.reply(
                    "Failed to generate art. You triggered their NSFW filter."
                )
                return

            if not image_base64:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.reply("Failed to generate art. Please try again later.")
                return

            with contextlib.suppress(discord.NotFound):
                await m.delete()

            await self.send_images(ctx, [base64.b64decode(image_base64.split(",")[1])]) 