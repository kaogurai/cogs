from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import humanize_list
import discord
import asyncio
import random
import aiohttp
import datetime

class AutoAvatar(commands.Cog):
    """automatically changes bot avatar"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=696969696969494)
        default_global = {"avatars": ['https://avatars.githubusercontent.com/u/23690422?s=400&v=4'], "current_avatar": ""}
        self.config.register_global(**default_global)
        self.avatar_task = asyncio.create_task(self.wait_for_avatar())

    def cog_unload(self):
        self.avatar_task.cancel()

    async def wait_for_avatar(self):
        await self.bot.wait_until_red_ready()
        while True:
            try:
                await self.change_avatar()
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                break
    
    async def change_avatar(self):
        all_avatars = await self.config.avatars()
        new_avatar = random.choice(all_avatars)
        async with aiohttp.ClientSession() as session:
            async with session.get(new_avatar) as request:
                avatar = await request.read()
        await self.bot.user.edit(avatar=avatar)
        await self.config.current_avatar.set(new_avatar)
        channel = self.bot.get_channel(818684148847345714)
        embed = discord.Embed(colour= await self.bot.get_embed_colour(channel), title= "Current Avatar", timestamp=datetime.datetime())
        embed.set_image(url=new_avatar)
        await channel.send(embed=embed)


    @commands.command()
    @commands.is_owner()
    async def addavatar(self, ctx, link: str):
        """adds an avatar to the list"""
        all_avatars = await self.config.avatars()
        if link.startswith('https://'):
            pass
        else:
            if link.startswith('http://'):
                pass
            else: 
                await ctx.send("That doesn't look like a valid link!")
                return
        if link not in all_avatars:
            all_avatars.append(link)
            await self.config.avatars.set(all_avatars)
            await ctx.tick()
        else:
            await ctx.send(f"{link} was already in my list of avatars, did you mean to remove it?")

    @commands.command()
    @commands.is_owner()
    async def removeavatar(self, ctx, link: str):
        """removes an avatar from the list"""
        all_avatars = await self.config.avatars()
        if link in all_avatars:
            all_avatars.remove(link)
            await self.config.avatars.set(all_avatars)
            await ctx.tick()
        else:
            await ctx.send(f"{link} wasn't in my list of avatars, did you mean to add it?")

    @commands.command()
    async def listavatars(self, ctx):
        """lists all links to rotating avatars"""
        all_avatars = await self.config.avatars()
        if not all_avatars:
            await ctx.send("Nothing. This might cause some errors, yikes!")
        paginator = discord.ext.commands.help.Paginator()
        for obj in all_avatars:
            paginator.add_line(obj)
        await ctx.send('List of all bot avatars:')
        for page in paginator.pages:
            await ctx.send(page)

    @commands.command()
    @commands.is_owner()
    async def forceavatar(self, ctx):
        """force changes avatar"""
        await self.change_avatar()
        await ctx.tick()

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def currentavatar(self,ctx):
        avatar = await self.config.current_avatar()
        embed = discord.Embed(colour= await self.bot.get_embed_colour(ctx.channel), title= "Current Avatar", timestamp=datetime.datetime)
        embed.set_image(url=avatar)
        await ctx.send(embed=embed)

    @commands.command()
    async def submitavatar(self, ctx, link: str):
        """submits a avatar"""
        if link.startswith('https://'):
            pass
        else:
            if link.startswith('http://'):
                pass
            else: 
                await ctx.send("That doesn't look like a valid link!")
                return
        channel = self.bot.get_channel(818239460004855888)
        embed = discord.Embed(colour= await self.bot.get_embed_colour(channel), title= "Avatar Submission", timestamp=datetime.datetime.now())
        embed.set_image(url=link)
        await channel.send(embed=embed)
        await ctx.tick()