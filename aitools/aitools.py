from redbot.core import commands, Config, checks
import discord
import aiohttp 
import urllib.parse

class AiTools(commands.Cog):
    """brainshop.ai cog"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=6574837465473)
        default_global = {"channels": [] }
        self.config.register_global(**default_global)

    @commands.command(aliases= ["ai"])
    async def talk(self, ctx, *, message: str):
        """Talk to a robot!"""
        brain_info = await ctx.bot.get_shared_api_tokens("brainshopai")
        if brain_info.get("brain_id") is None:
            return await ctx.send("The brain id has not been set.")
        if brain_info.get("brain_key") is None:
            return await ctx.send("The brain key has not been set.")

        url= "http://api.brainshop.ai/get?bid=" + brain_info.get("brain_id") + "&key=" + brain_info.get("brain_key") + "&uid=" + str(ctx.author.id) + "&msg=" + urllib.parse.quote(message)

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as request:
                response = await request.json()
                await ctx.send(response['cnt'])

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return
        channel_list = await self.config.channels()
        if not channel_list:
            return
        if message.channel.id not in channel_list:
            return
        brain_info = await self.bot.get_shared_api_tokens("brainshopai")

        if brain_info.get("brain_id") is None:
            return await message.channel.send("The brain id has not been set.")
        if brain_info.get("brain_key") is None:
            return await message.channel.send("The brain key has not been set.")

        url= "http://api.brainshop.ai/get?bid=" + brain_info.get("brain_id") + "&key=" + brain_info.get("brain_key") + "&uid=" + str(message.author.id) + "&msg=" + urllib.parse.quote(str(message.content))

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as request:
                response = await request.json()
                await message.channel.send(response['cnt'])
        
    @commands.group()
    @commands.guild_only()
    @commands.admin()
    async def aichannel(self, ctx):
        """configure the ai channels"""
         
    @aichannel.command()
    async def add(self, ctx, channel: discord.TextChannel):
        """Add a channel for the AI to talk in."""
        if not channel:
            channel = ctx.channel

        channel_list = await self.config.channels()

        if channel.id not in channel_list:
            channel_list.append(channel.id)
            await self.config.channels.set(channel_list)
            await ctx.send(f"Okay, I've added {channel.mention} to the config.")
        else:
            await ctx.send(f"{channel.mention} is already in the config! Did you mean to use the remove command?")
        
    @aichannel.command()
    async def remove(self, ctx, channel: discord.TextChannel):
        """Remove a channel for the AI to talk in."""
        if not channel:
            channel = ctx.channel
        channel_list = await self.config.channels()
        if channel.id in channel_list:
            channel_list.remove(channel.id)
            await self.config.channels.set(channel_list)
            await ctx.send(f"Okay, I've removed {channel.mention} from the config.")
        else:
            await ctx.send(f"{channel.mention} wasn't in the config! Did you mean to use the add command?")