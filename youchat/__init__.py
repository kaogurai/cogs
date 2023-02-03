from redbot.core.bot import Red

from .youchat import YouChat


async def setup(bot: Red):
    cog = YouChat(bot)
    bot.add_cog(cog)


__red_end_user_data_statement__ = "This cog does not store any end user data. The API used may have different policies."
