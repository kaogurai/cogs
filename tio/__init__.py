from redbot.core.bot import Red

from .tio import Tio


def setup(bot: Red):
    bot.add_cog(Tio(bot))


__red_end_user_data_statement__ = "This cog does not store any end user data."
