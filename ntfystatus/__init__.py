from redbot.core.bot import Red

from .ntfystatus import NTFYStatus


async def setup(bot: Red):
    cog = NTFYStatus(bot)
    bot.add_cog(cog)


__red_end_user_data_statement__ = "This cog does not store any end user data."
