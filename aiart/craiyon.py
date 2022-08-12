import asyncio
import base64
import contextlib
from io import BytesIO

import discord
from PIL import Image
from redbot.core import commands
from redbot.core.commands import Context
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

from .abc import MixinMeta


class CraiyonCommand(MixinMeta):
    """
    Implements the Internal Craiyon API used in their web client.
    """

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def craiyon(self, ctx: Context, *, text: str):
        """
        Generate art using Craiyon. (dalle-mini/mega)
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
                        await ctx.reply("Failed to generate art. Please try again later.")
                        return
                else:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
                    await ctx.reply("Failed to generate art. Please try again later.")
                    return

            images = json["images"]
            image_list = [
                Image.open(BytesIO(base64.b64decode(image))) for image in images
            ]

            width = max(image.width for image in image_list)
            height = max(image.height for image in image_list)

            new_image = Image.new("RGB", (width * 3, height * 3))

            for i in range(3):
                for j in range(3):
                    new_image.paste(image_list[i * 3 + j], (width * j, height * i))

            buffer = BytesIO()
            new_image.save(buffer, format="PNG")
            buffer.seek(0)

            with contextlib.suppress(discord.NotFound):
                await m.delete()

            embed = discord.Embed(
                title="Here's your art!",
                description="Type the number next to the image to select it. If you want more than one image, seperate the numbers with a comma.",
                color=await ctx.embed_color(),
            )
            embed.set_image(url="attachment://craiyon.png")
            file = discord.File(buffer, "craiyon.png")

            is_nsfw = await self.check_nsfw(buffer.getvalue())
            if is_nsfw:
                m = await ctx.reply(
                    "These images may contain NSFW content. Would you like me to DM them to you?"
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
                            "Failed to send image. Please make sure you have DMs enabled."
                        )

                else:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
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
                selected = [int(i) for i in msg.content.split(",")]
                selected = [image_list[i - 1] for i in selected]
            except:
                return

            for image in selected:
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                buffer.seek(0)
                if is_nsfw:
                    await ctx.author.send(file=discord.File(buffer, "craiyon.png"))
                else:
                    await ctx.send(file=discord.File(buffer, "craiyon.png"))
