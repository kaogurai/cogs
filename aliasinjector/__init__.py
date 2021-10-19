from .aliasinjector import AliasInjector


async def setup(bot):
    cog = AliasInjector(bot)
    bot.add_cog(cog)


__red_end_user_data_statement__ = "This cog does not store any end user data."
