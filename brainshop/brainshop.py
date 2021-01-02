from redbot.core import commands, config, checks
import aiohttp 
import urllib.parse

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

        url= "http://api.brainshop.ai/get?bid=" + brain_id + "&key=" + brain_key + "&uid=" + str(ctx.author.id) + "&msg=" + urllib.parse.quote(message)

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as request:
                response = await request.json()
                await ctx.send(response['cnt'])
        
    @commands.group()
    @commands.mod()
    async def brainset(self, ctx):
        """Configure the AI! This does not currently work."""
         
    
    @brainset.group()
    @commands.admin()
    async def channel(self, ctx):
        """Manage the channels the AI talks in."""

    @channel.command()
    async def add(self, ctx):
        """Add a channel for the AI to talk in."""
    @channel.command()
    async def remove(self, ctx):
        """Remove a channel for the AI to talk in."""
    @channel.command()
    async def list(self, ctx):
        """View all the channels that the AI will talk in."""
         
    
    @brainset.group()
    @commands.mod()
    async def blacklist(self, ctx):
        """Blacklist people from using the AI."""

    @blacklist.command()
    async def add(self, ctx):
        """Add people to the blacklist."""
    @blacklist.command()
    async def remove(self, ctx):
        """Remove people from the blacklist."""
    @blacklist.command()
    async def list(self, ctx):
        """View the blacklist."""
         