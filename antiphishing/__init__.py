from .antiphishing import AntiPhishing


async def setup(bot):
    cog = AntiPhishing(bot)
    bot.add_cog(cog)


__red_end_user_data_statement__ = "This cog does not store any end user data."
