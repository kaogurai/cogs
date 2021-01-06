from redbot.core import commands
import discord


class Randomcmds(commands.Cog):
    """things that fit nowhere else"""

    @commands.command()
    async def asia(self, ctx):
       await ctx.send("asia is the best person on this earth and loves videos of emo kids dancing")
       await ctx.send("https://cdn.discordapp.com/attachments/768663090337677315/795133511673053225/emokidsyummy.mp4")

    @commands.command()
    async def maddie(self, ctx):
        embed=discord.Embed(description="maddie is a cool cat + is emotionally attached to this cat’s birthday party :revolving_hearts::revolving_hearts::revolving_hearts::revolving_hearts:", color=11985904, image = "https://cdn.discordapp.com/attachments/768663090337677315/796118254128332820/image0.jpg")
        await ctx.send(embed=embed)
    @commands.command()
    async def oofchair(self, ctx):
       await ctx.send("oof is p cool :) he's also a bot developer! check out his bot here: http://pwnbot.xyz/")
