from typing import Optional

import aiohttp
import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import Context

FLOWERY_API_URL = "https://api.flowery.pw/v1"


class OCR(commands.Cog):
    """
    Converts an image to text.
    """

    __version__ = "2.0.0"

    def __init__(self, bot: Red):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx: Context):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    @commands.command()
    async def ocr(self, ctx: Context, link: Optional[str] = None):
        """
        Convert an image to text.

        You can either upload an image or provide a direct link.

        Supported formats: jpg, png, webp, gif, bmp, raw, ico
        """
        if not link and not ctx.message.attachments:
            await ctx.send("Please provide an image to convert to text.")
            return

        if not link:
            link = str(ctx.message.attachments[0].url)

        async with ctx.typing():
            headers = {
                "User-Agent": f"Red-DiscordBot, OCR/{self.__version__} (https://github.com/kaogurai/cogs)"
            }
            async with self.session.get(
                f"{FLOWERY_API_URL}/ocr",
                params={
                    "url": link,
                },
                headers=headers,
            ) as resp:
                if resp.status == 404:
                    await ctx.send("No text was found in the image.")
                    return
                elif resp.status == 400:
                    await ctx.send("Image could not be accessed or is in wrong format.")
                    return
                elif resp.status != 200:
                    await ctx.send("Something went wrong when trying to get the text.")
                    return

                data = await resp.json()

        embed = discord.Embed(
            title="OCR Results",
            color=await ctx.embed_color(),
            description=data["text"][:4000],
            url=link,
        )
        await ctx.send(embed=embed)
