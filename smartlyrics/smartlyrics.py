from redbot.core import commands

class SmartLyrics(commands.Cog):
    """get lyrics of your current playing song"""

    @commands.command()
    @commands.is_owner()
    async def lyrics(self, ctx, song: str=None):
        """get lyrics of your current playing song"""
        await ctx.send("Yeah, this isn't done.")