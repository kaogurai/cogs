from redbot.core import commands
import aiohttp

class Brainshop(commands.Cog):
    """brainshop.ai cog"""

    @commands.command()
    async def talk(self, ctx, message: str):
        """Talk to a robot!"""
        # add code here
        brain_info = await ctx.bot.get_shared_api_tokens("brainshopai")
        if brain_info.get("brain_id") is None:
            return await ctx.send("The brain id has not been set.")
        if brain_info.get("brain_key") is None:
            return await ctx.send("The brain key has not been set.")

        await ctx.send("no")