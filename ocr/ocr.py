from io import BytesIO
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

    __version__ = "1.0.3"

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

    @commands.command()
    async def mathocr(self, ctx: Context, link: Optional[str] = None):
        """
        Get the math equation from an image.
        """
        if not link and not ctx.message.attachments:
            await ctx.send("Please provide an image to convert to a math problem.")
            return

        if not link:
            link = str(ctx.message.attachments[0].url)

        async with ctx.typing():
            headers = {
                "User-Agent": f"Red-DiscordBot, OCR/{self.__version__} (https://github.com/kaogurai/cogs)"
            }
            async with self.session.get(
                f"{FLOWERY_API_URL}/mathocr",
                params={
                    "url": link,
                },
                headers=headers,
            ) as resp:
                if resp.status == 404:
                    await ctx.send("No equations were found in the image.")
                    return
                elif resp.status == 400:
                    await ctx.send("Image could not be accessed or is in wrong format.")
                    return
                elif resp.status != 200:
                    await ctx.send(
                        "Something went wrong when trying to get the equations."
                    )
                    return

                data = await resp.json()

            def e(x):
                return "`" + x + "`"

            embed = discord.Embed(
                color=await ctx.embed_color(), title="Math OCR Results"
            )
            embed.add_field(name="Text", value=e(data["text"][:1000]))
            embed.add_field(name="ASCII Math", value=e(data["ascii"][:1000]))
            embed.add_field(name="LaTeX", value=e(data["latex"][:1000]))
            embed.add_field(name="MathML", value=e(data["latex"][:1000]))

            post_data = {
                "auth": {"user": "guest", "password": "guest"},
                "latex": data["latex"],
                "resolution": 600,
                "color": "000000",
            }
            async with self.session.post(
                "http://latex2png.com/api/convert",
                json=post_data,
            ) as r:
                if r.status != 200:
                    await ctx.send(
                        "Something went wrong when getting an image of the LaTeX."
                    )
                    return
                latex_json_data = await r.json()
                async with self.session.get(
                    "http://latex2png.com" + latex_json_data["url"]
                ) as r:
                    if r.status != 200:
                        await ctx.send(
                            "Something went wrong when getting an image of the LaTeX."
                        )
                        return
                    latex_image_data = await r.read()
                    latex_image_data = BytesIO(latex_image_data)
                    latex_image_data.seek(0)
                    embed.set_image(url="attachment://latex.png")

        await ctx.send(embed=embed, file=discord.File(latex_image_data, "latex.png"))
