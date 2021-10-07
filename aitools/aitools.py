import asyncio
import urllib.parse

import aiohttp
import discord
import contextlib
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.predicates import MessagePredicate

try:
    from redbot.core.utils._dpy_menus_utils import dpymenu

    DPY_MENUS = True
except ImportError:
    from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
    DPY_MENUS = False


class AiTools(commands.Cog):
    """https://brainshop.ai cog"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.config = Config.get_conf(self, identifier=6574837465473)
        default_guild = {"channels": []}
        self.config.register_guild(**default_guild)
        self.channel_cache = {}
        self.bot.loop.create_task(self.fill_channel_cache())

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def fill_channel_cache(self):
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            self.channel_cache[guild] = all_guilds[guild]["channels"]

    async def request_brainshop(self, author, brain_info, message):
        """Get a response from the Brainshop API"""
        brain_id = brain_info.get("brain_id")
        brain_key = brain_info.get("brain_key")
        author_id = str(author.id)
        message = urllib.parse.quote(message)
        url = f"http://api.brainshop.ai/get?bid={brain_id}&key={brain_key}&uid={author_id}&msg={message}"
        async def thing(self, url):
            async with self.session.get(url) as response:
                if response.status == 200:
                    j = await response.json()
                    return j.get("cnt")
                elif response.status == 408:
                    # brainshop LOVES to time out
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            j = await response.json()
                            return j.get("cnt")
        try:
            results = await thing(self, url)
        except aiohttp.ServerDisconnectedError:
            try:
                results = await thing(self, url)
            except:
                results = None
        except aiohttp.ClientConnectorError:
            results = None
        return results

    @commands.command(aliases=["ai", "robot"])
    async def talk(self, ctx, *, message: str):
        """Talk to a robot!"""
        brain_info = await ctx.bot.get_shared_api_tokens("brainshopai")
        if brain_info.get("brain_id") is None:
            return await ctx.send("The brain id has not been set.")
        if brain_info.get("brain_key") is None:
            return await ctx.send("The brain key has not been set.")
        try:
            r = await self.request_brainshop(ctx.author, brain_info, message)
        except:
           return await ctx.send("Something went wrong. Try again in a little bit")
        if r is None:
            return await ctx.send("Something went wrong. Try again in a little bit.")
        await ctx.send(r)

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
        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return

        try:
            channel_list = self.channel_cache[message.guild.id]
        except KeyError:
            return

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
            r = await self.request_brainshop(
                message.author, brain_info, message.clean_content
            )
        except:
            return await message.channel.send("Something went wrong. Try again in a little bit")
        if r is None:
            return await message.channel.send(
                "Something went wrong. Try again in a little bit."
            )
        await message.channel.send(r)

    @commands.group()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
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
            self.channel_cache[ctx.guild.id] = channel_list
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
            self.channel_cache[ctx.guild.id] = channel_list
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
            await ctx.send("The AI is not set to talk in any channels.")
        else:
            try:
                m = await ctx.send(
                    "Are you sure you want to clear all the channels that the ai talks in? Respond with yes or no."
                )
                predictate = MessagePredicate.yes_or_no(ctx, user=ctx.author)
                await ctx.bot.wait_for("message", check=predictate, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send(
                    "You never responded, please use the command again to clear all the channels."
                )
                return
            if predictate.result:
                await self.config.guild(ctx.guild).channels.clear()
                self.channel_cache[ctx.guild.id] = []
                await ctx.tick()
                with contextlib.supress(discord.NotFound):
                    await m.delete()

            else:
                await ctx.send("Ok, I won't clear any channels.")

    @aichannel.command()
    async def list(self, ctx):
        """List all the channels the AI will talk in."""
        try:
            channel_list = self.channel_cache[ctx.guild.id]
        except KeyError:
            channel_list = None
        if not channel_list:
            await ctx.send("There's no channels in the config.")
        else:
            text = "".join(
                "<#" + str(channel) + "> - " + str(channel) + "\n"
                for channel in channel_list
            )
            pages = [p for p in pagify(text=text, delims="\n")]
            embeds = []
            for index, page in enumerate(pages):
                embed = discord.Embed(
                    title="Automatic AI Channels",
                    color=await ctx.embed_colour(),
                    description=page,
                )
                if len(embeds) > 1:
                    embed.set_footer(text=f"Page {index+1}/{len(pages)}")
                embeds.append(embed)

            if DPY_MENUS:
                await dpymenu(ctx, embeds, timeout=60)
            else:
                if len(pages) == 1:
                    await ctx.send(embed=embeds[0])
                else:
                    await menu(ctx, embeds, DEFAULT_CONTROLS, timeout=60)
