from .phisherman import PhisherMan


async def setup(bot):
    cog = PhisherMan(bot)
    bot.add_cog(cog)


__red_end_user_data_statement__ = "This cog does not store any end user data."
