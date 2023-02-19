from typing import Optional

import aiohttp
import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import pagify


class YouChat(commands.Cog):
    """
    Use YouChat via a Discord bot.
    """

    __version__ = "1.0.1"

    def __init__(self, bot: Red):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.config = Config.get_conf(self, identifier=420)
        self.config.register_global(token=None)
        self.bot.loop.create_task(self.initialize())

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx: Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def initialize(self) -> None:
        config_token = await self.config.token()
        if config_token is None:
            async with self.session.get("https://api.betterapi.net/gen") as resp:
                if resp.status == 200:
                    j = await resp.json()
                    await self.config.token.set(j["key"])

    async def get_response(self, message: str) -> Optional[str]:
        """
        Get a response from the chatbot.
        """
        token = await self.config.token()
        if token is None:
            return

        async with self.session.get(
            f"https://api.betterapi.net/youdotcom/chat?message={message}&key={token}"
        ) as resp:
            if (
                resp.status == 200 and resp.content_type == "application/json"
            ):  # this stupid ass api returns 200 even when it's down
                j = await resp.json()
                return j["message"]

    @commands.command(aliases=["ychat", "yc"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def youchat(self, ctx: Context, *, message: str):
        """
        Use YouChat via a Discord bot.
        """
        async with ctx.typing():
            response = await self.get_response(message)
            if response is None:
                await ctx.send("Something went wrong. Please try again later.")
            else:
                pages = [
                    p for p in pagify(text=response, delims="\n", page_length=4096)
                ]
                title = "YouChat"
                for page in pages:
                    embed = discord.Embed(
                        description=page,
                        color=await ctx.embed_color(),
                    )
                    if title:
                        embed.title = title

                        try:
                            await ctx.reply(embed=embed)
                        except discord.NotFound:
                            await ctx.send(embed=embed)
                    else:
                        await ctx.send(embed=embed)

                    title = None
