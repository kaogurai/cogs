from redbot.core import commands, Config, checks
from redbot.core.utils.chat_formatting import humanize_list
import discord
import aiohttp
import urllib.parse


class AiTools(commands.Cog):
    """https://brainshop.ai cog"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.config = Config.get_conf(self, identifier=6574837465473)
        default_guild = {"channels": []}
        self.config.register_guild(**default_guild)

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    @commands.command(aliases=["ai", "robot"])
    async def talk(self, ctx, *, message: str):
        """Talk to a robot!"""
        brain_info = await ctx.bot.get_shared_api_tokens("brainshopai")
        if brain_info.get("brain_id") is None:
            return await ctx.send("The brain id has not been set.")
        if brain_info.get("brain_key") is None:
            return await ctx.send("The brain key has not been set.")
        try:
            async with self.session.get(
                "http://api.brainshop.ai/get?bid="
                + brain_info.get("brain_id")
                + "&key="
                + brain_info.get("brain_key")
                + "&uid="
                + str(ctx.author.id)
                + "&msg="
                + urllib.parse.quote(message)
            ) as request:
                response = await request.json()
                await ctx.send(response["cnt"])
        except:
            await ctx.send("Uh oh, an error occured!")

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return
        if not message.channel.permissions_for(message.guild.me).send_messages:
            return
        if await self.bot.allowed_by_whitelist_blacklist(who=message.author) is False:
            return
        channel_list = await self.config.guild(message.guild).channels()
        if not channel_list:
            return
        if message.channel.id not in channel_list:
            return
        brain_info = await self.bot.get_shared_api_tokens("brainshopai")

        if brain_info.get("brain_id") is None:
            return await message.channel.send("The brain id has not been set.")
        if brain_info.get("brain_key") is None:
            return await message.channel.send("The brain key has not been set.")

        try:
            async with self.session.get(
                "http://api.brainshop.ai/get?bid="
                + brain_info.get("brain_id")
                + "&key="
                + brain_info.get("brain_key")
                + "&uid="
                + str(message.author.id)
                + "&msg="
                + urllib.parse.quote(str(message.content))
            ) as request:
                response = await request.json()
                await message.channel.send(response["cnt"])
        except:
            await message.channel.send("Uh oh, an error occured!")

    @commands.group()
    @commands.guild_only()
    @commands.mod_or_permissions(manage_guild=True)
    async def aichannel(self, ctx):
        """Configure the channels the AI will talk in."""
        pass

    @aichannel.command()
    async def add(self, ctx, channel: discord.TextChannel):
        """Add a channel for the AI to talk in."""
        channel_list = await self.config.guild(ctx.guild).channels()
        if channel.id not in channel_list:
            channel_list.append(channel.id)
            await self.config.guild(ctx.guild).channels.set(channel_list)
            await ctx.tick()
        else:
            await ctx.send(
                f"{channel.mention} was already in the config, did you mean to remove it?"
            )

    @aichannel.command()
    async def remove(self, ctx, channel: discord.TextChannel):
        """Remove a channel for the AI to stop talking in."""
        channel_list = await self.config.guild(ctx.guild).channels()
        if channel.id in channel_list:
            channel_list.remove(channel.id)
            await self.config.guild(ctx.guild).channels.set(channel_list)
            await ctx.tick()
        else:
            await ctx.send(
                f"I couldn't find {channel.mention} in the config, did you mean to add it?"
            )

    @aichannel.command()
    async def clear(self, ctx):
        """Remove all the channels the AI will talk in."""
        channel_list = await self.config.guild(ctx.guild).channels()
        if not channel_list:
            await ctx.send("There's no channels in the config.")
        else:
            await self.config.guild(ctx.guild).channels.set([])
            await ctx.tick()

    @aichannel.command()
    async def list(self, ctx):
        """List all the channels the AI will talk in."""
        channel_list = await self.config.guild(ctx.guild).channels()
        if not channel_list:
            await ctx.send("There's no channels in the config.")
        else:
            lolidk = ""
            for obj in channel_list:
                lolidk = lolidk + "\n <#" + str(obj) + "> - " + str(obj)
            embed = discord.Embed(
                title="AI Channels", color=await ctx.embed_colour(), description=lolidk
            )
            await ctx.send(embed=embed)
