from redbot.core.bot import Red

from .kaotools import KaoTools


async def setup(bot: Red):
    await bot.add_cog(KaoTools(bot))


__red_end_user_data_statement__ = "This cog does not store any end user data."
