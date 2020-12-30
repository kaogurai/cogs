from redbot.core import commands
import aiohttp

class Brainshop(commands.Cog):
    """brainshop.ai cog - for this to work, you will need to get a brain from https://brainshop.ai and [p]set api brainshopai brain_id <id> brain_key <key>"""

    @commands.command()
    async def talk(self, ctx, user: str):
        """Talk to a robot!"""
        # add code here
        brain_info = await self.bot.get_shared_api_tokens(brainshopai)
        if brainshopai.get("brain_id") is None:
            return await ctx.send("The brain id has not been set.")
        if brainshopai.get("brain_key") is None:
            return await ctx.send("The brain key has not been set.")

        await ctx.send("no")