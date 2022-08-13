import datetime
import random
import re
import time
from typing import Optional

import aiohttp
import discord
import psutil
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import (
    humanize_list,
    humanize_number,
    humanize_timedelta,
    pagify,
)
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .abc import CompositeMetaClass
from .image import ImageMixin
from .media import MediaMixin
from .owner import OwnerCommands
from .text import TextMixin

SUPPORT_SERVER = "https://discord.gg/p6ehU9qhg8"


class KaoTools(
    ImageMixin,
    MediaMixin,
    OwnerCommands,
    TextMixin,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    """
    Random tools for kaogurai.
    """

    __version__ = "1.0.1"

    KAO_API_URL = "https://api.kaogurai.xyz/v1"

    def __init__(self, bot: Red):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        setattr(
            bot._connection,
            "parse_interaction_create",
            self.parse_interaction_create,
        )
        bot._connection.parsers["INTERACTION_CREATE"] = self.parse_interaction_create
        self.bot.loop.create_task(self.set_token())

    def cog_unload(self):
        del self.bot._connection.parsers["INTERACTION_CREATE"]
        self.bot.loop.create_task(self.session.close())

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx: Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def invite_url(self, snowflake: Optional[int] = None) -> str:
        scopes = ("bot", "applications.commands")
        permissions = discord.Permissions(1642790907127)
        if snowflake:
            return discord.utils.oauth_url(
                snowflake, permissions, scopes=("bot", "applications.commands")
            )
        app_info = await self.bot.application_info()
        return discord.utils.oauth_url(app_info.id, permissions, scopes=scopes)

    # https://github.com/Kowlin/Sentinel/blob/master/slashinjector/core.py
    def parse_interaction_create(self, data: dict):
        self.bot.dispatch("interaction_create", data)

    async def set_token(self):
        token = await self.bot.get_shared_api_tokens("omdb")
        self.omdb_key = token.get("key")

    @commands.Cog.listener()
    async def on_red_api_tokens_update(self, service_name: str, api_tokens: dict):
        if service_name == "omdb":
            self.omdb_key = api_tokens.get("key")

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if not message.channel.permissions_for(message.guild.me).send_messages:
            return
        if await self.bot.allowed_by_whitelist_blacklist(who=message.author) is False:
            return
        app = await self.bot.application_info()
        if not re.compile(rf"^<@!?{app.id}>$").match(message.content):
            return
        prefixes = await self.bot.get_prefix(message.channel)
        if f"<@!{app.id}> " in prefixes:
            prefixes.remove(f"<@!{app.id}> ")
        sorted_prefixes = sorted(prefixes, key=len)
        if len(sorted_prefixes) > 500:
            return
        prefixes_s = "es" if len(sorted_prefixes) > 1 else ""
        are_is = "are" if len(sorted_prefixes) > 1 else "is"
        d = (
            "**Hey there!**\n"
            f"My prefix{prefixes_s} in this server {are_is} {humanize_list(prefixes)}\n"
            f"You can type `{sorted_prefixes[0]}help` to view all commands!\n"
        )
        embed = discord.Embed(
            colour=await self.bot.get_embed_colour(message.channel), description=d
        )
        await message.channel.send(embed=embed)

    @commands.command(aliases=["yt", "ytsearch", "youtubesearch"])
    async def youtube(self, ctx: Context, *, video: str):
        """
        Search for a youtube video.
        Inspired by Aikaterna's YouTube cog
        """
        async with self.session.get(
            f"{self.KAO_API_URL}/youtube/search", params={"query": video}
        ) as r:
            if r.status != 200:
                await ctx.send("An error occurred while searching for videos.")
                return
            data = await r.json()
        if not data:
            await ctx.send("Nothing found.")
            return

        data = [video["url"] for video in data]

        await menu(ctx, data, DEFAULT_CONTROLS)

    @commands.command(aliases=["ytm", "ytmsearch", "youtubemusicsearch"])
    async def youtubemusic(self, ctx: Context, *, video: str):
        """
        Search for a video on youtube music.
        Inspired by Aikaterna's YouTube cog
        """
        async with self.session.get(
            f"{self.KAO_API_URL}/youtube/musicsearch", params={"query": video}
        ) as r:
            if r.status != 200:
                await ctx.send("An error occurred while searching for videos.")
                return
            data = await r.json()
        if not data:
            await ctx.send("Nothing found.")
            return

        data = [video["url"] for video in data]

        await menu(ctx, data, DEFAULT_CONTROLS)

    @commands.command()
    @commands.bot_has_permissions(add_reactions=True, use_external_emojis=True)
    async def poll(self, ctx: Context, *, question: str):
        """
        Create a simple poll.
        """
        if len(question) > 2000:
            await ctx.send("That question is too long.")
            return
        message = await ctx.send(f"**{ctx.author} asks:** " + question)
        await message.add_reaction("👍")
        await message.add_reaction("<:idk:838887174345588796>")
        await message.add_reaction("👎")

    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["support", "inv"])
    async def invite(self, ctx: Context, *, bot: Optional[discord.User] = None):
        """
        Invite me or another bot!
        """
        if bot is None:
            t = "I am a private bot."
            d = f"It is not possible to invite me at this time."
            embed = discord.Embed(
                color=await ctx.embed_color(),
                title=t,
                description=d,
            )
            await ctx.send(embed=embed)
            return

        if not bot.bot:
            await ctx.send("That user isn't a bot, dumbass.")
            return

        embed = discord.Embed(
            title=f"Click here to invite {bot}!",
            color=await ctx.embed_color(),
            url=await self.invite_url(bot.id),
        )
        embed.set_footer(text="Note: this link may not work for some bots.")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def membercount(self, ctx: Context):
        """
        Get the current amount of members in the server.
        """
        count = len(ctx.guild.members)
        await ctx.send(f"There are currently **{count}** members in this server.")

    @commands.command(aliases=["someone", "pickuser", "randommember", "picksomeone"])
    @commands.guild_only()
    async def randomuser(self, ctx: Context):
        """
        Pick a random user in the server.
        """
        await ctx.send(f"<@{random.choice(ctx.guild.members).id}>")

    @commands.command(aliases=["colour"])
    @commands.bot_has_permissions(embed_links=True)
    async def color(self, ctx: Context, color: discord.Colour):
        """
        View information and a preview of a color.
        """
        async with self.session.get(
            f"https://www.thecolorapi.com/id?hex={str(color)[1:]}"
        ) as r:
            if r.status == 200:
                data = await r.json()
            else:
                await ctx.send(
                    "Something is wrong with the API I use, please try again later."
                )
                return

        embed = discord.Embed(color=color, title=data["name"]["value"])
        embed.set_thumbnail(
            url=f"https://api.alexflipnote.dev/color/image/{str(color)[1:]}"
        )
        embed.set_image(
            url=f"https://api.alexflipnote.dev/color/image/gradient/{str(color)[1:]}"
        )
        embed.description = (
            "```yaml\n"
            f"Hex: {color}\n"
            f"RGB: {data['rgb']['value']}\n"
            f"HSL: {data['hsl']['value']}\n"
            f"HSV: {data['hsv']['value']}\n"
            f"CMYK: {data['cmyk']['value']}\n"
            f"XYZ: {data['XYZ']['value']}"
            "```"
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=["av"])
    @commands.bot_has_permissions(embed_links=True)
    async def avatar(self, ctx: Context, user: Optional[discord.User] = None):
        """
        Get a user's avatar.
        """
        if not user:
            user = ctx.author
        png = user.avatar_url_as(format="png", size=4096)
        jpg = user.avatar_url_as(format="jpg", size=4096)
        gif = user.avatar_url_as(static_format="png", size=4096)
        size_512 = user.avatar_url_as(size=512)
        size_1024 = user.avatar_url_as(size=1024)
        size_2048 = user.avatar_url_as(size=2048)
        size_4096 = user.avatar_url_as(size=4096)
        m = (
            f"Formats: [PNG]({png}) | [JPG]({jpg}) | [GIF]({gif})\n"
            f"Sizes: [512]({size_512}) | [1024]({size_1024}) | [2048]({size_2048}) | [4096]({size_4096})"
        )
        embed = discord.Embed(
            color=await ctx.embed_color(),
            title=f"{user.name}'s avatar",
            description=m,
        )
        embed.set_image(url=user.avatar_url_as(size=4096))
        await ctx.send(embed=embed)

    @commands.command(aliases=["oldestmessage"])
    @commands.bot_has_permissions(read_message_history=True, embed_links=True)
    async def firstmessage(
        self, ctx: Context, channel: Optional[discord.TextChannel] = None
    ):
        """
        Gets the first message in a channel.
        """
        c = channel if channel else ctx.channel
        first = await c.history(limit=1, oldest_first=True).flatten()
        if first:
            t = "Click here to jump to the first message."
            e = discord.Embed(
                color=await ctx.embed_color(),
                title=t,
                url=first[0].jump_url,
            )
            await ctx.send(embed=e)
        else:
            await ctx.send("No messages found.")

    @commands.command(aliases=["listemojis", "emojilist"])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_emojis=True)
    async def listemoji(self, ctx: Context, list_urls: bool = False):
        """
        Lists all custom emojis on the server.

        If `list_urls` is True, the URLs of the emojis will be returned instead of ids.
        """
        guild = ctx.guild
        emojis = guild.emojis
        if not emojis:
            return await ctx.send("This server has no custom emojis.")

        msg = f"Custom emojis in {guild.name}:\n"

        for emoji in emojis:
            if list_urls:
                msg += f"{emoji} - `:{emoji.name}:` (<{emoji.url}>)\n"
            else:
                if emoji.animated:
                    msg += f"{emoji} - `:{emoji.name}:` (`<a:{emoji.name}:{emoji.id}>`)\n"
                else:
                    msg += f"{emoji} - `:{emoji.name}:` (`<:{emoji.name}:{emoji.id}>`)\n"

        for page in pagify(msg):
            await ctx.send(page)

    @commands.command()
    async def botstats(self, ctx: Context):
        """
        View statistics about [botname].
        """
        red_proccess = psutil.Process()

        with red_proccess.oneshot():
            memory_amount = int(red_proccess.memory_info().rss / 1024 ** 2)
            memory_usage = red_proccess.memory_percent("rss")
        delta = datetime.datetime.utcnow() - self.bot.uptime
        uptime_str = humanize_timedelta(timedelta=delta) or "Less than one second."

        embed = discord.Embed(
            color=await ctx.embed_color(),
            title="Statistics",
        )
        embed.add_field(
            name="Process",
            value=(
                f"• Memory Usage: {memory_amount} MB ({str(memory_usage)[:4]}%)\n"
                f"• Uptime: {uptime_str}"
            ),
        )
        embed.add_field(
            name="Bot",
            value=(
                f"• Guild Count: {humanize_number(len(self.bot.guilds))}\n"
                f"• User Count: {humanize_number(len(self.bot.users))}\n"
                f"• Average Users: {humanize_number(int(len(self.bot.users) / len(self.bot.guilds)))}\n"
            ),
        )
        cog = self.bot.get_cog("CommandStats")
        if cog:
            embed.add_field(
                name="Command Stats",
                value=(
                    f"• Commands Executed: {humanize_number(sum((await cog.config.all())['globaldata'].values()))}\n"
                    f"• Commands Executed this session: {humanize_number(sum(cog.session.values()))}\n (since <t:{int(cog.session_time.timestamp())}>)\n"
                    f"• Commands Executed this session per minute: {str(humanize_number(sum([cog.session[x] for x in cog.session]) / (time.time() - cog.session_time.timestamp() )*60))[:4]}"
                ),
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command(alises=["echo"])
    @commands.admin_or_permissions(administrator=True)
    async def say(
        self, ctx: Context, channel: Optional[discord.TextChannel], *, message: str
    ):
        """
        Make the bot say something.

        Only the first 2048 characters of the message are sent.
        """
        if not channel:
            channel = ctx.channel
        await channel.send(
            message[:2048],
            allowed_mentions=discord.AllowedMentions(
                everyone=False, roles=False, users=True
            ),
        )

    @commands.command(aliases=["saydelete", "echodelete"])
    @commands.bot_has_permissions(manage_messages=True)
    @commands.admin_or_permissions(administrator=True)
    async def sayd(
        self, ctx: Context, channel: Optional[discord.TextChannel], *, message: str
    ) -> None:
        """
        Make the bot say something, and delete the message that invoked it.

        Only the first 2048 characters of the message are sent.
        """
        if not channel:
            channel = ctx.channel
        await ctx.message.delete()
        await channel.send(
            message[:2048],
            allowed_mentions=discord.AllowedMentions(
                everyone=False, roles=False, users=True
            ),
        )

    @commands.command(aliases=["saymention", "echomention"])
    @commands.bot_has_permissions(mention_everyone=True)
    @commands.admin_or_permissions(administrator=True)
    async def saym(
        self, ctx: Context, channel: Optional[discord.TextChannel], *, message: str
    ):
        """
        Make the bot say something, but mentions are allowed.

        Only the first 2048 characters of the message are sent.
        """
        if not channel:
            channel = ctx.channel
        await channel.send(
            message[:2048],
            allowed_mentions=discord.AllowedMentions(
                everyone=True, roles=True, users=True
            ),
        )
