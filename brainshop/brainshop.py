from redbot.core import commands

class Brainshop(commands.Cog):
    """brainshop.ai cog - for this to work, you will need to get a brain from https://brainshop.ai and [p]set api brainshop.ai brain_id <id> brain_key <key>"""

    @commands.command()
    async def mycom(self, ctx):
        """This does stuff!"""
        # Your code will go here
        await ctx.send("I can do stuff!")