import asyncio
import contextlib
import random
import string
from io import BytesIO

import discord
from redbot.core import commands
from redbot.core.commands import Context
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

from .abc import MixinMeta


class StableDiffusionCommand(MixinMeta):
    """
    Implements the Pixelz API for Stable Diffusion.
    """

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def stablediffusion(self, ctx: Context, *, text: str):
        """
        Generate art using Stable Diffusion.
        """
        if len(text) > 239:
            await ctx.reply("The text needs to be 239 characters or less.")
            return

        m = await ctx.reply("Generating art... This may take a while.")
        async with ctx.typing():
            user_id = "".join(
                random.choice(string.ascii_letters + string.digits) for _ in range(28)
            )

            data = {
                "prompts": [
                    {
                        "prompt": text,
                        "weight": 1,
                        "public": True,
                    }
                ],
                "public": True,
                "style": "stable",
                "user_id": user_id,
            }

            async with self.session.post(
                "https://api.pixelz.ai/preview", json=data
            ) as req:
                if req.status != 200:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
                    await ctx.reply("Failed to generate art. Please try again later.")
                    return
                json = await req.json()

            if json["success"] is False:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.reply("Failed to generate art. Please try again later.")
                return

            image_id = json["process"]["generated_image_id"]

            for x in range(60):
                if x == 59:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
                    await ctx.reply("Failed to generate art. Please try again later.")
                    return

                headers = {
                    "Referer": "https://pixelz.ai/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
                }
                async with self.session.get(
                    f"https://storage.googleapis.com/pixelz-images/{user_id}/{image_id}/preview.jpg",
                    headers=headers,
                ) as req:
                    if req.status == 200:
                        data = await req.read()
                        break

                await asyncio.sleep(15)

            with contextlib.suppress(discord.NotFound):
                await m.delete()

            embed = discord.Embed(
                title="Here's your art!",
                description="Type the number next to the image to select it. If you want more than one image, seperate the numbers with a comma.",
                color=await ctx.embed_color(),
            )
            embed.set_image(url="attachment://stablediffusion.jpg")
            file = discord.File(BytesIO(data), "stablediffusion.jpg")

            is_nsfw = await self.check_nsfw(data)
            if is_nsfw:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()

                m = await ctx.reply(
                    "These images may contain NSFW content. Would you like me to DM you the image?"
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
                        await m.edit(content="Sending images...")
                    try:
                        await ctx.author.send(embed=embed, file=file)
                    except discord.Forbidden:
                        await ctx.reply(
                            "Failed to send images. Please make sure you have DMs enabled."
                        )
                    return
            else:
                await ctx.reply(embed=embed, file=file)

            def check(m):
                if is_nsfw:
                    return m.author == ctx.author and m.channel == ctx.author.dm_channel
                else:
                    return m.author == ctx.author and m.channel == ctx.channel

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=60)
            except asyncio.TimeoutError:
                return

            try:
                selected = [int(i) - 1 for i in msg.content.split(",")]
            except:
                return

            for image in selected:
                # data = {
                #    "user_id": user_id,
                #    "image_id": image_id,
                #    "output_index": image,
                # }
                # async with self.session.post("https://api.pixelz.ai/upscale", json=data) as req:
                #    ...

                async with self.session.get(
                    f"https://storage.googleapis.com/pixelz-images/{user_id}/{image_id}/{image}.png"
                ) as req:
                    if req.status != 200:
                        with contextlib.suppress(discord.NotFound):
                            await m.delete()
                        await ctx.reply("Failed to download art. Please try again later.")
                        return
                    data = await req.read()

                buffer = BytesIO(data)

                if is_nsfw:
                    await ctx.author.send(
                        file=discord.File(buffer, "stablediffusion.png")
                    )
                else:
                    if selected[0] == image:
                        await ctx.reply(file=discord.File(buffer, "stablediffusion.png"))
                    else:
                        await ctx.send(file=discord.File(buffer, "stablediffusion.png"))
