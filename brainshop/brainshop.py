from redbot.core import commands
import aiohttp 

class Brainshop(commands.Cog):
    """brainshop.ai cog"""

    @commands.command()
    async def talk(self, ctx, *, message: str):
       
        """Talk to a robot!"""

        brain_info = await ctx.bot.get_shared_api_tokens("brainshopai")
        if brain_info.get("brain_id") is None:
            return await ctx.send("The brain id has not been set.")
        if brain_info.get("brain_key") is None:
            return await ctx.send("The brain key has not been set.")
        brain_id = brain_info.get("brain_id")
        brain_key = brain_info.get("brain_key")

        messagefix = message.replace(" ", "+")

        url= "http://api.brainshop.ai/get?bid=" + brain_id + "&key=" + brain_key + "&uid=" + str(ctx.author.id) + "&msg=" + messagefix

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as request:
                response = await request.json()
                await ctx.send(response['cnt'])