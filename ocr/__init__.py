from redbot.core.bot import Red

from .ocr import OCR


async def setup(bot: Red):
    cog = OCR(bot)
    bot.add_cog(cog)


__red_end_user_data_statement__ = "This cog does not store any end user data."
