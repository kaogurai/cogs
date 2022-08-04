from redbot.core.bot import Red

from .kaotools import KaoTools


def setup(bot: Red):
    bot.add_cog(KaoTools(bot))


__red_end_user_data_statement__ = "This cog does not store any end user data."
