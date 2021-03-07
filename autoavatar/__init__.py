from redbot.core.bot import Red
from .autoavatar import AutoAvatar

async def setup(bot: Red) -> None:
    cog = AutoAvatar(bot)
    bot.add_cog(cog)