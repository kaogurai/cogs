import asyncio
import contextlib
import datetime
import random
import re
import urllib
from abc import ABC
from io import BytesIO

import aiohttp
import discord
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .guildmanager import GuildManager
from .image import ImageMixin
from .owner import OwnerCommands
from .text import TextMixin

SUPPORT_SERVER = "https://discord.gg/p6ehU9qhg8"


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """Another thing I stole from last.fm for ABC"""


class KaoTools(
    GuildManager,
    ImageMixin,
    OwnerCommands,
    TextMixin,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    """
    Random bot tools.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=10023)
        default_global = {
            "blacklist": [],
            "whitelist": [],
        }
        self.config.register_global(**default_global)
        self.session = aiohttp.ClientSession()
        setattr(
            bot._connection,
            "parse_interaction_create",
            self.parse_interaction_create,
        )
        bot._connection.parsers["INTERACTION_CREATE"] = self.parse_interaction_create

    def cog_unload(self):
        del self.bot._connection.parsers["INTERACTION_CREATE"]
        self.bot.loop.create_task(self.session.close())
        self.bot.loop.create_task(self.deezerclient.http.close())

    async def red_delete_data_for_user(self, **kwargs):
        return

    async def search_youtube(self, query):
        """
        Query lavalink's /loadtracks endpoint for a list of tracks.
        """
        cog = self.bot.get_cog("Audio")
        if not cog:
            return
        config = await cog.config.all()
        if not config["use_external_lavalink"]:
            password = "youshallnotpass"
            host = "localhost"
            port = 2333
        else:
            password = config["password"]
            host = config["host"]
            port = config["ws_port"]
        params = {"identifier": "ytsearch:" + query}
        headers = {"Authorization": password, "Accept": "application/json"}
        async with self.session.get(
            f"http://{host}:{port}/loadtracks",
            params=params,
            headers=headers,
        ) as request:
            if request.status == 200:
                response = await request.json()
                with contextlib.suppress(KeyError):
                    return response["tracks"]

    async def invite_url(self, snowflake: int = None) -> str:
        """
        Generates the invite URL for the bot.

        Returns
        -------
        str
            Invite URL.
        """
        scopes = ("bot", "applications.commands")
        permissions = discord.Permissions(397283945463)
        if snowflake:
            return discord.utils.oauth_url(snowflake, permissions, scopes=scopes)
        app_info = await self.bot.application_info()
        return discord.utils.oauth_url(app_info.id, permissions, scopes=scopes)

    # https://github.com/Kowlin/Sentinel/blob/master/slashinjector/core.py
    def parse_interaction_create(self, data):
        self.bot.dispatch("interaction_create", data)

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

    @commands.command(aliases=["yt"])
    async def youtube(self, ctx, *, video: str):
        """
        Search for a youtube video.
        Inspired by Aikaterna's YouTube cog
        """
        results = await self.search_youtube(video)
        if not results:
            await ctx.send("Nothing found.")
            return

        await ctx.send(results[0]["info"]["uri"])

    @commands.command(aliases=["yts", "ytsearch"])
    async def youtubesearch(self, ctx, *, video: str):
        """
        Search for a youtube video with a menu of results.
        Inspired by Aikaterna's YouTube cog
        """
        results = await self.search_youtube(video)
        if not results:
            await ctx.send("Nothing found.")
            return
        urls = []
        for result in results:
            urls.append(result["info"]["uri"])
        await menu(ctx, urls, DEFAULT_CONTROLS, timeout=60)

    @commands.command()
    @commands.bot_has_permissions(add_reactions=True, use_external_emojis=True)
    async def poll(self, ctx, *, question: str):
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
    async def invite(self, ctx, *, bot: discord.User = None):
        """
        Invite me or another bot!
        """
        if bot is None:
            t = "Click here to invite me."
            d = f"If you need help with the bot, click [here]({SUPPORT_SERVER})"
            embed = discord.Embed(
                color=await ctx.embed_color(),
                title=t,
                url=await self.invite_url(),
                description=d,
            )
            embed.set_footer(
                text="Note: You need 50 members and 50% of your member count must be human."
            )
            await ctx.send(embed=embed)
            return

        if not bot.bot:
            await ctx.send("That user isn't a bot.")
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
    async def membercount(self, ctx):
        """
        Get the current amount of members in the server.
        """
        count = len(ctx.guild.members)
        await ctx.send(f"There are currently **{count}** members in this server.")

    @commands.command(aliases=["someone", "pickuser", "randommember", "picksomeone"])
    @commands.guild_only()
    async def randomuser(self, ctx):
        """
        Pick a random user in the server.
        """
        await ctx.send(f"<@{random.choice(ctx.guild.members).id}>")

    @commands.command(aliases=["colour"])
    @commands.bot_has_permissions(embed_links=True)
    async def color(self, ctx, color: discord.Colour):
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
    async def avatar(self, ctx, user: discord.User = None):
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
        self, ctx: commands.Context, channel: discord.TextChannel = None
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
    async def listemoji(self, ctx: commands.Context, list_urls: bool = False):
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

    @commands.command(aliases=["definition", "synonym", "antonym"])
    async def define(self, ctx, *, thing_to_define: str):
        """Define a word or phrase."""
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(thing_to_define)}"
        async with self.session.get(url) as resp:
            if resp.status == 404:
                await ctx.send("I couldn't find a definition for that.")
                return
            if resp.status != 200:
                await ctx.send("Something went wrong when trying to get the definition.")
                return
            data = await resp.json()
        embeds = []
        for i, result in enumerate(data):
            embed = discord.Embed(color=await ctx.embed_color())
            if "partOfSpeech" in result["meanings"][0]:
                embed.title = (
                    f"{result['word']} ({result['meanings'][0]['partOfSpeech']})"
                )
            else:
                embed.title = result["word"]
            if (
                "phonetics" in result
                and result["phonetics"]
                and "audio" in result["phonetics"][0]
            ):
                audio = result["phonetics"][0]["audio"]
                embed.url = f"https:{audio}"
            embed.description = result["meanings"][0]["definitions"][0]["definition"]
            if "example" in result["meanings"][0]["definitions"][0]:
                embed.add_field(
                    name="Example",
                    value=result["meanings"][0]["definitions"][0]["example"],
                )
            if result["meanings"][0]["definitions"][0]["synonyms"]:
                embed.add_field(
                    name="Synonyms",
                    value=", ".join(result["meanings"][0]["definitions"][0]["synonyms"]),
                )
            if result["meanings"][0]["definitions"][0]["antonyms"]:
                embed.add_field(
                    name="Antonyms",
                    value=", ".join(result["meanings"][0]["definitions"][0]["antonyms"]),
                )
            if len(data) > 1:
                embed.set_footer(text=f"Result {i + 1}/{len(data)}")
            embeds.append(embed)
        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            await menu(ctx, embeds, DEFAULT_CONTROLS)

    @commands.command(aliases=["dl", "musicdl", "musicdownload"])
    @commands.bot_has_permissions(attach_files=True, add_reactions=True, embed_links=True)
    async def download(self, ctx, *, song: str):
        """
        Download a song.
        """
        async with ctx.typing():
            async with self.session.get(
                "https://slider.kz/vk_auth.php", params={"q": song}
            ) as req:
                if req.status != 200:
                    await ctx.send("Something went wrong when trying to get the song.")
                    return
                data = await req.json()
            audios = data["audios"][""]
            if not audios:
                await ctx.send("I couldn't find that song!")
                return

            for audio in audios:
                name = urllib.parse.quote(audio["tit_art"])
                ex = "null"
                if audio["extra"]:
                    ex = audio["extra"]
                extra = urllib.parse.quote(ex)
                url = f"https://slider.kz/download/{audio['id']}/{audio['duration']}/{audio['url']}/{name}.mp3?extra={extra}"
                audio["url"] = url

            if len(audios) > 1:
                embeds = []
                m = ""
                for i, audio in enumerate(audios):
                    duration = str(datetime.timedelta(seconds=audio["duration"]))
                    m += f"{i + 1}. {audio['tit_art']} ({duration})\n"
                pages = [p for p in pagify(text=m, delims="\n", page_length=512)]
                for i, page in enumerate(pages):
                    t = "Which song do you want to download?"
                    embed = discord.Embed(color=await ctx.embed_color(), title=t)
                    embed.description = page
                    f = "Type the number of the song you want to download."
                    if len(pages) > 1:
                        f += f" | Page {i + 1}/{len(pages)}"
                    embed.set_footer(text=f)
                    embeds.append(embed)
                if len(embeds) == 1:
                    await ctx.send(embed=embeds[0])
                else:
                    self.bot.loop.create_task(menu(ctx, embeds, DEFAULT_CONTROLS))

                def check(m):
                    return m.author == ctx.author and m.channel == ctx.channel

                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=60)
                except asyncio.TimeoutError:
                    await ctx.send("You took too long to respond.")
                    return

                try:
                    index = int(msg.content) - 1
                    audio = audios[index]
                except (ValueError, IndexError):
                    await ctx.send("That's not a valid number.")
                    return

                async with self.session.get(audio["url"]) as resp:
                    if resp.status != 200:
                        await ctx.send(
                            "Something went wrong when trying to get the song."
                        )
                        return
                    data = await resp.read()

                if ctx.guild:
                    limit = ctx.guild.filesize_limit
                else:
                    limit = 8000000

                if len(data) > limit:
                    embed = discord.Embed(
                        color=await ctx.embed_color(),
                        description=f"That song is too big to send on discord. Click [here]({audio['url']}) to download it.",
                        url=audio["url"],
                    )
                    await ctx.send(embed=embed)
                else:
                    biof = BytesIO(data)
                    biof.seek(0)
                    await ctx.send(
                        file=discord.File(biof, filename=f"{audio['tit_art']}.mp3")
                    )
