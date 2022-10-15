import asyncio
import contextlib
import math
from copy import copy
from io import BytesIO
from typing import List, Optional

import aiohttp
import discord
from PIL import Image
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

from .abc import CompositeMetaClass
from .clip import CLIPCommand
from .craiyon import CraiyonCommand
from .latentdiffusion import LatentDiffusionCommand
from .pixelz import PixelzCommand
from .playgroundai import PlaygroundAI
from .upscale import UpscaleCommand
from .waifudiffusion import WaifuDiffusionCommand
from .wombo import WomboCommand


class AIArt(
    CLIPCommand,
    CraiyonCommand,
    PixelzCommand,
    PlaygroundAI,
    LatentDiffusionCommand,
    UpscaleCommand,
    WaifuDiffusionCommand,
    WomboCommand,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    """
    Generate incredible art using AI.
    """

    __version__ = "1.12.2"

    def __init__(self, bot: Red):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx: Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def _check_nsfw(self, data: bytes) -> bool:
        """
        Params:
            data: bytes - The raw image data to check.

        Returns:
            bool - Whether the image is NSFW or not.
        """
        async with self.session.post(
            "https://api.kaogurai.xyz/v1/nsfwdetection/image", data={"file": data}
        ) as req:
            if req.status == 200:
                resp = await req.json()
                if "error" in resp.keys():
                    return False
                results = resp["safeSearchAnnotation"]
                is_nsfw = ["LIKELY", "VERY_LIKELY"]
                if results["adult"] in is_nsfw or results["racy"] in is_nsfw:
                    return True
            return False

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
        columns = int(_columns) if _columns.is_integer() else int(_columns) + 1

        # Get the width and height of each image
        width = max(image.width for image in image_list)
        height = max(image.height for image in image_list)

        # Create a new image with the correct size
        grid = Image.new("RGB", (width * columns, height * rows))

        # Paste the images into the correct position
        for index, image in enumerate(image_list):
            grid.paste(image, (width * (index % columns), height * (index // columns)))

        buffer = BytesIO()
        grid.save(buffer, format="WEBP")
        buffer.seek(0)

        return buffer.read()

    async def compress_image(self, image_data: bytes) -> Optional[bytes]:
        """
        Params:
            image: bytes - The image to compress.

        Returns:
            Optional[bytes] - The compressed image.
        """

        def func():
            try:
                image = Image.open(BytesIO(image_data))
                image = image.convert("RGB")

                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=75, optimize=True)
                buffer.seek(0)
                return buffer.read()
            except Exception:
                ...

        return await self.bot.loop.run_in_executor(None, func)

    async def get_image_mimetype(self, data: bytes) -> Optional[str]:
        """
        Params:
            data: bytes - The image data to get the mimetype of.

        Returns:
            Optional[str] - The mimetype of the image.
        """

        def func():
            image = Image.open(BytesIO(data))
            return image.format

        with contextlib.suppress(Exception):
            return await self.bot.loop.run_in_executor(None, func)

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

    async def send_images(self, ctx: Context, images: List[bytes]) -> None:
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
                embed.set_footer(text="Image selection will time out in 5 minutes.")

            file = discord.File(BytesIO(image), filename="image.webp")

            is_nsfw = await self._check_nsfw(image)
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
                    await m.edit(content="Sending images...")
                try:
                    await ctx.author.send(embed=embed, file=file)
                except discord.Forbidden:
                    await ctx.reply(
                        "Failed to send image. Please make sure you have DMs enabled."
                    )
        else:
            await ctx.reply(embed=embed, file=file)

        if len(images) > 1:

            def check(m):
                if is_nsfw:
                    return m.author == ctx.author and m.channel == ctx.author.dm_channel
                else:
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
                if is_nsfw:
                    await ctx.author.send(
                        file=discord.File(BytesIO(image), filename="image.png")
                    )
                else:
                    await ctx.send(
                        file=discord.File(BytesIO(image), filename="image.png")
                    )

    @commands.group(
        aliases=["text2art", "text2im", "text2img", "text2image"],
        invoke_without_command=True,
    )
    async def draw(self, ctx: Context, *, args: str):
        """
        Draw an image using AI.

        Currently this proxies towards the Stable Diffusion command.
        """
        msg = copy(ctx.message)
        msg.content = f"{ctx.prefix}stablediffusion {args}"
        self.bot.dispatch("message", msg)
