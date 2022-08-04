from redbot.core.bot import Red

from .antiphishing import AntiPhishing


async def setup(bot: Red):
    cog = AntiPhishing(bot)
    bot.add_cog(cog)


__red_end_user_data_statement__ = "This cog does not store any end user data."
