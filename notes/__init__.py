from .notes import Notes


async def setup(bot):
    cog = Notes(bot)
    bot.add_cog(cog)


__red_end_user_data_statement__ = "This cog stores notes on individual users created by moderators. Only moderators can remove them."
