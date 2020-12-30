from redbot.core import commands

class Mycog(commands.Cog):
    """brainshop.ai cog"""

    @commands.command()
    async def mycom(self, ctx):
        """This does stuff!"""
        # Your code will go here
        await ctx.send("I can do stuff!")