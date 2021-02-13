from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_list
import discord
import re

old_invite = None

class KaoTools(commands.Cog):
    """general commands for kaogurai"""

    def __init__(self, bot):
        self.bot = bot

    def cog_unload(self):
        global old_invite
        if old_invite:
            try:
                self.bot.remove_command("invite")
            except:
                pass
            self.bot.add_command(old_invite)

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if not re.compile(rf"^<@!?{self.bot.user.id}>$").match(message.content):
            return
        embed = discord.Embed(colour= await self.bot.get_embed_colour(message.channel), description= f"""
        **Hey there!** <a:bounce:778449468717531166>
        My prefixes in this server are {humanize_list(await self.bot.get_prefix(message.channel))}
        You can view all my commands with `{(await self.bot.get_prefix(message.channel))[2]}help`
        Need some help? Join my [support server!](https://discord.gg/p6ehU9qhg8)
        """)
        await message.channel.send(embed=embed)

    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def invite(self, ctx):
       """invite me!"""
       embed = discord.Embed(title="Thanks for using me!", colour=await ctx.embed_colour(), url="https://kaogurai.xyz")
       embed.set_thumbnail(url= ctx.me.avatar_url)
       embed.add_field(name="Bot Invite", value=(f"[Click Here!](https://discord.com/oauth2/authorize?client_id={ctx.me.id}&scope=bot&permissions=2147483647)"), inline=True)
       embed.add_field(name="Support Server", value="[Click Here!](https://discord.gg/p6ehU9qhg8)", inline=True)
       await ctx.send(embed=embed)

    @commands.command()
    async def asia(self, ctx):
        """emo kids lover"""
        await ctx.send("asia is the best person on this earth and loves videos of emo kids dancing")
        await ctx.send("https://cdn.discordapp.com/attachments/768663090337677315/795133511673053225/emokidsyummy.mp4")
        
    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def maddie(self, ctx):
        """cool cat"""
        embed=discord.Embed(description="maddie is a cool cat + is emotionally attached to this cat’s birthday party :revolving_hearts::revolving_hearts::revolving_hearts::revolving_hearts:", color=11985904)
        embed.set_image(url = "https://cdn.discordapp.com/attachments/768663090337677315/796118254128332820/image0.jpg")
        await ctx.send(embed=embed)

    @commands.command()
    async def oofchair(self, ctx):
       """cool bot dev"""
       await ctx.send("oof is p cool :) he's also a bot developer! check out his bot here: http://pwnbot.xyz/")
       
def setup(bot):
    kaotools = KaoTools(bot)
    global old_invite
    old_invite = bot.get_command("invite")
    if old_invite:
        bot.remove_command(old_invite.name)
    bot.add_cog(kaotools)