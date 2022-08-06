import aiohttp
import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import Context

from .session import BlenderBotSession


class BlenderBot(commands.Cog):
    """
    Discord version of blenderbot.ai.
    """

    __version__ = "1.0.2"

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
    @commands.max_concurrency(1, commands.BucketType.user)
    async def blenderbot(self, ctx: Context):
        """
        Start a BlenderBot session.
        """
        embed = discord.Embed(
            title="Starting BlenderBot session...", color=await ctx.embed_colour()
        )
        embed.add_field(
            name="Warning",
            value=(
                "This is a Meta (Facebook) research project, so be careful when sharing any data. "
                "If you share any personal data, there is no way of deleting it.\n\n"
                "**Do not share:**\n"
                "- Names\n"
                "- Emails\n"
                "- Birthdays\n"
                "- Addresses\n"
                "- Phone numbers\n"
            ),
        )
        embed.add_field(
            name="Closing Sesssion",
            value="Type `close session` to close the session. Unused sessions will be closed after 1 minute.",
        )
        await ctx.send(embed=embed)

        session = BlenderBotSession(self.session, ctx)
        await session.start_session()
