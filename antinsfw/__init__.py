from redbot.core.bot import Red
from .antinsfw import AntiNSFW

async def setup(bot: Red) -> None:
    cog = AntiNSFW(bot)
    bot.add_cog(cog)

__red_end_user_data_statement__ = (
    "This cog does not store any end user data."
)