from redbot.core.bot import Red

from .search import Search


async def setup(bot: Red):
    cog = Search(bot)
    await bot.add_cog(cog)


__red_end_user_data_statement__ = "This cog does not store any end user data."
