from redbot.core.bot import Red
from .aitools import AiTools

async def setup(bot: Red) -> None:
    cog = AiTools(bot)
    bot.add_cog(cog)