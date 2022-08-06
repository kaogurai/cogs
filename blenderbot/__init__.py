from redbot.core.bot import Red

from .blenderbot import BlenderBot


async def setup(bot: Red):
    cog = BlenderBot(bot)
    bot.add_cog(cog)


__red_end_user_data_statement__ = (
    "This cog does not store any end user data. Meta may store data though, who knows!"
)
