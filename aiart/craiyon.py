import asyncio
import base64
from io import BytesIO

import discord
from PIL import Image
from redbot.core import commands
from redbot.core.commands import Context

from .abc import MixinMeta


class CraiyonCommand(MixinMeta):
    """
    Implements the Internal Craiyon API used in their web client.
    """

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def craiyon(self, ctx: Context, *, text: str):
        """
        Generate art using Craiyon (dalle-mini/mega)
        """
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
                        await ctx.send("Failed to generate art. Please try again later.")
                else:
                    await ctx.send("Failed to generate art. Please try again later.")
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

            embed = discord.Embed(
                title="Here's your art!",
                description="Type the number next to the image to select it. If you want more than one image, seperate the numbers with a comma.",
                color=await ctx.embed_color(),
            )
            embed.set_image(url="attachment://craiyon.png")
            await ctx.send(embed=embed, file=discord.File(buffer, "craiyon.png"))

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30)
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
                await ctx.send(file=discord.File(buffer, "craiyon.png"))
