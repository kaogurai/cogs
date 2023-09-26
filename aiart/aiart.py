import asyncio
import contextlib
import math
from io import BytesIO
from typing import List, Optional

import aiohttp
import discord
from PIL import Image
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import Context

from .abc import CompositeMetaClass
from .nemusona import NemuSonaCommands
from .wombo import WomboCommand


class AIArt(
    NemuSonaCommands,
    WomboCommand,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    """
    Generate incredible art using AI.
    """

    __version__ = "2.1.1"

    def __init__(self, bot: Red):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.api_token = None
        self.bot.loop.create_task(self.set_token())

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx: Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def set_token(self) -> None:
        """
        Possibly sets the token for the Wombo Dream API.
        """
        tokens = await self.bot.get_shared_api_tokens("wombo")
        self.api_token = tokens.get("token")

    @commands.Cog.listener()
    async def on_red_api_tokens_update(self, service_name: str, api_tokens: dict):
        """
        Updates the token when the API tokens are updated.
        Possibly sets the token for the Wombo Dream API.
        """
        if service_name == "wombo":
            self.api_token = api_tokens.get("token")

    def _generate_grid(self, images: List[bytes]) -> bytes:
        """
        Params:
            images: List[bytes] - The images to generate a grid for.

        Returns:
            bytes - The grid image.

        -----------------------------

        The number of images needs to be a perfect square.
        """
        image_list = [Image.open(BytesIO(image)) for image in images]

        # Get the number of rows and columns
        rows = int(math.sqrt(len(image_list)))
        _columns = math.sqrt(len(image_list))
        columns = int(_columns) if _columns.is_integer() else int(_columns + 1.5)

        # Get the width and height of each image
        width = max(image.width for image in image_list)
        height = max(image.height for image in image_list)

        # Create a new image with the correct size
        grid = Image.new("RGBA", (width * columns, height * rows))

        # Paste the images into the correct position
        for index, image in enumerate(image_list):
            grid.paste(image, (width * (index % columns), height * (index // columns)))

        buffer = BytesIO()
        grid.save(buffer, format="WEBP")
        buffer.seek(0)

        return buffer.read()

    async def get_image(self, url: str) -> Optional[str]:
        """
        Params:
            url: str - The image URL to get.

        Returns:
            Optional[str] - The image data.
        """
        with contextlib.suppress(Exception):
            async with self.session.get(url) as req:
                if req.status == 200:
                    return await req.read()

    async def send_images(
        self, ctx: Context, images: List[bytes], footer: Optional[str] = ""
    ) -> None:
        """
        Params:
            images: List[bytes] - The images to send.
        """
        async with ctx.typing():
            if len(images) == 1:
                image = images[0]
            else:
                image = await self.bot.loop.run_in_executor(
                    None, self._generate_grid, images
                )

            embed = discord.Embed(
                title="Here's your image" + ("s" if len(images) > 1 else "") + "!",
                color=await ctx.embed_color(),
            )
            embed.set_image(url="attachment://image.webp")
            if len(images) > 1:
                embed.description = "Type the number of the image to download it. If you want more than one image, seperate the numbers with a comma. If you want all of the images, type `all`."

                if footer:
                    footer += " | "
                footer += "Image selection will time out in 5 minutes."

            embed.set_footer(text=footer)

            file = discord.File(BytesIO(image), filename="image.webp")

        await ctx.reply(embed=embed, file=file)

        if len(images) > 1:

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=300)
            except asyncio.TimeoutError:
                return

            try:
                if msg.content.lower() == "all":
                    selected = images
                else:
                    selected = [int(i) for i in msg.content.split(",")]
                    selected = [images[i - 1] for i in selected]
            except:
                return

            for image in selected:
                await ctx.send(file=discord.File(BytesIO(image), filename="image.png"))
