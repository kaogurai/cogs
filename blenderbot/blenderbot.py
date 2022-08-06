import asyncio

import aiohttp
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import Context

from .session import BlenderBotSession


class BlenderBot(commands.Cog):
    """
    Discord version of blenderbot.ai.
    """

    __version__ = "1.0.1"

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

    @commands.command()
    async def blenderbot(self, ctx: Context):
        """
        Start a BlenderBot session.

        The session will be closed if you don't send a message in 30 seconds.
        """
        await ctx.send("Starting session...")
        session = BlenderBotSession(self.session, ctx)
        asyncio.create_task(session.start_session())
