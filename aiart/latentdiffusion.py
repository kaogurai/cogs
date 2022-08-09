import asyncio
import base64
import random
import string
from io import BytesIO

import discord
import contextlib
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate
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
        Generate art using Latent Diffusion
        """
        if len(text) > 250:
            await ctx.send("The text needs to be 250 characters or less.")
            return

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
                "https://hf.space/embed/multimodalart/latentdiffusion/api/queue/push/", json=data
            ) as req:
                if req.status != 200:
                    await ctx.send("Failed to generate art. Please try again later.")
                    return
                
                json = await req.json()

            data = {
                "hash": json["hash"],
            }

            for x in range(120):
                if x == 119:
                    await ctx.send("Failed to generate art. Please try again later.")
                    return

                async with self.session.post(
                    "https://hf.space/embed/multimodalart/latentdiffusion/api/queue/status/", json=data
                ) as req:
                    if req.status != 200:
                        await ctx.send("Failed to generate art. Please try again later.")
                        return
                    
                    json = await req.json()

                    if json["status"] == "COMPLETE":
                        break

                await asyncio.sleep(5)

            image_bytes = base64.b64decode(json["data"]["data"][0].split(",")[1])
            
            image = BytesIO(image_bytes)
            image.seek(0)

            embed = discord.Embed(
                title="Here's your art!",
                color=await ctx.embed_color(),
            )
            embed.set_image(url="attachment://latentdiffusion.png")
            file = discord.File(image, "latentdiffusion.png")

            if ctx.guild and not ctx.channel.is_nsfw():

                is_nsfw = await self.check_nsfw(image_bytes)
                if is_nsfw:

                    m = await ctx.send(
                        f"{ctx.author.mention}, this image may contain NSFW content. Would you like me to DM you the image?"
                    )
                    start_adding_reactions(m, ReactionPredicate.YES_OR_NO_EMOJIS)
                    pred = ReactionPredicate.yes_or_no(m, ctx.author)
                    try:
                        await ctx.bot.wait_for("reaction_add", check=pred, timeout=60)
                    except asyncio.TimeoutError:
                        with contextlib.suppress(discord.NotFound):
                            await m.delete()
                        return
                    if pred.result is True:
                        with contextlib.suppress(discord.NotFound):
                            await m.edit(
                                content=f"{ctx.author.mention}, sending image..."
                            )
                        try:
                            await ctx.author.send(embed=embed, file=file)
                        except discord.Forbidden:
                            await ctx.send(
                                "Failed to send image. Please make sure you have DMs enabled."
                            )
                        return
                    else:
                        with contextlib.suppress(discord.NotFound):
                            await m.delete()
                        return

            await ctx.send(embed=embed, file=file, content=ctx.author.mention)

                
