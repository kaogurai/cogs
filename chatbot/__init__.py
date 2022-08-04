from redbot.core.bot import Red

from .chatbot import ChatBot


async def setup(bot: Red):
    cog = ChatBot(bot)
    bot.add_cog(cog)


__red_end_user_data_statement__ = "This cog does not store any end user data. The API used (brainshop.ai) may have different policies."
