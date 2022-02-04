from .wombo import Wombo


async def setup(bot):
    cog = Wombo(bot)
    bot.add_cog(cog)


__red_end_user_data_statement__ = "This cog does not store any end user data."
