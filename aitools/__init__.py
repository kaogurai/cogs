from redbot.core.bot import Red
from .aitools import AiTools


async def setup(bot: Red) -> None:
    cog = AiTools(bot)
    bot.add_cog(cog)


__red_end_user_data_statement__ = "This cog does not store any end user data. The API (https://brainshop.ai) may store data, but that is unable to be deleted."
