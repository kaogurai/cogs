from redbot.core.bot import Red

from .notes import Notes


async def setup(bot: Red) -> None:
    cog = Notes(bot)
    bot.add_cog(cog)


__red_end_user_data_statement__ = "This cog stores notes on individual users created by moderators. Only moderators can remove them."
