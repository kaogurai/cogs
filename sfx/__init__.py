from redbot.core.bot import Red

from .sfx import SFX


async def setup(bot: Red):
    cog = SFX(bot)
    await bot.add_cog(cog)


__red_end_user_data_statement__ = "This cog stores a user's voice name, links to their join and leave sounds, and if their TTS should be translated. All this data is able to be deleted."
