from copy import copy

import aiohttp
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import Context

from .abc import CompositeMetaClass
from .craiyon import CraiyonCommand
from .pixelz import PixelzCommand
from .wombo import WomboCommand


class AIArt(
    CraiyonCommand,
    PixelzCommand,
    WomboCommand,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    """
    Generate incredible art using AI.
    """

    __version__ = "1.2.0"

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

    async def check_nsfw(self, data: bytes) -> bool:
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

    @commands.group(
        aliases=["text2art", "text2im", "text2img", "text2image"],
        invoke_without_command=True,
    )
    async def draw(self, ctx: Context, *, args: str):
        """
        Draw an image using AI.

        Currently this proxies towards the wombo command.
        """
        msg = copy(ctx.message)
        msg.content = f"{ctx.prefix}wombo {args}"
        self.bot.dispatch("message", msg)
