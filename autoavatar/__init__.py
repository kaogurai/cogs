from redbot.core.bot import Red
from .autoavatar import AutoAvatar


async def setup(bot: Red) -> None:
    cog = AutoAvatar(bot)
    bot.add_cog(cog)


__red_end_user_data_statement__ = "This cog does not store any end user data."
