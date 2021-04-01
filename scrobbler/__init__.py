from redbot.core.bot import Red
from .scrobbler import Scrobbler

async def setup(bot: Red) -> None:
    cog = Scrobbler(bot)
    bot.add_cog(cog)

__red_end_user_data_statement__ = (
    "Girl gimme a sec."
)