import asyncio
import contextlib
from io import BytesIO

import discord
from redbot.core import commands
from redbot.core.commands import Context
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

from .abc import MixinMeta


class DalleCommand(MixinMeta):
    """
    Implements the playground AI API for Dall-E 2.
    """

    @commands.command(aliases=["dalle2", "d2"])
    @commands.bot_has_permissions(embed_links=True)
    async def dalle(self, ctx: Context, *, text: str):
        """
        Generate art using Dall-E 2.
        """
        m = await ctx.reply("Generating art... This may take a while.")
        async with ctx.typing():
            json = {
                "prompt": text,
                "modelType": "dalle-2",
                "isPrivate": True,
            }
            cookies = {
                "__Secure-next-auth.session-token": "eca9ae53-49c6-47ba-a5c9-51b599ca2aa8"
            }
            async with self.session.post(
                "https://playgroundai.com/api/models",
                json=json,
                cookies=cookies,
            ) as req:
                if req.status == 200:
                    json = await req.json()
                else:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
                    if "filter" in await req.text():
                        await ctx.send(
                            "Your prompt triggered the NSFW filters. Please try again with a different prompt."
                        )
                        return
                    await ctx.reply("Failed to generate art. Please try again later.")
                    return

            async with self.session.get(json["images"][0]["url"]) as req:
                if req.status == 200:
                    image = BytesIO(await req.read())
                else:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
                    await ctx.reply("Failed to download. Please try again later.")
                    return

            with contextlib.suppress(discord.NotFound):
                await m.delete()

            embed = discord.Embed(
                title="Here's your art!",
                color=await ctx.embed_color(),
            )
            embed.set_image(url="attachment://dalle2.png")
            file = discord.File(image, "dalle2.png")

            is_nsfw = await self.check_nsfw(image.getvalue())
            if is_nsfw:
                m = await ctx.reply(
                    "These images may contain NSFW content. Would you like me to DM them to you?"
                )
                start_adding_reactions(m, ReactionPredicate.YES_OR_NO_EMOJIS)
                pred = ReactionPredicate.yes_or_no(m, ctx.author)
                try:
                    await ctx.bot.wait_for("reaction_add", check=pred, timeout=300)
                except asyncio.TimeoutError:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
                    return
                if pred.result is True:
                    with contextlib.suppress(discord.NotFound):
                        await m.edit(content="Sending image...")
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
