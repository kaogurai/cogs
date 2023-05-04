from redbot.core.bot import Red

from .ytdl import YTDL


async def setup(bot: Red):
    cog = YTDL(bot)
    await bot.add_cog(cog)


__red_end_user_data_statement__ = "This cog does not store any end user data."
