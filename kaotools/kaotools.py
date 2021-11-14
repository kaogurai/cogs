import contextlib
import random
from .deezer import Deezer
import re
import sys
import time
import urllib

import aiohttp
import discord
import redbot
from redbot.core import commands
from redbot.core.utils._dpy_menus_utils import dpymenu
from redbot.core.utils.chat_formatting import humanize_list, pagify
from copy import copy
from zalgo_text import zalgo

SUPPORT_SERVER = "https://discord.gg/p6ehU9qhg8"


class KaoTools(commands.Cog):
    """Random tools for kaogurai that fit nowhere else."""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.deezerclient = Deezer()
        setattr(
            bot._connection, "parse_interaction_create", self.parse_interaction_create
        )
        bot._connection.parsers["INTERACTION_CREATE"] = self.parse_interaction_create

    def cog_unload(self):
        del self.bot._connection.parsers["INTERACTION_CREATE"]
        self.bot.loop.create_task(self.session.close())
        self.bot.loop.create_task(self.deezerclient.http.close())

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
            f"http://{host}:{port}/loadtracks", params=params, headers=headers
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
        permissions = discord.Permissions(6408367871)
        if snowflake:
            return discord.utils.oauth_url(snowflake, permissions, scopes=scopes)
        app_info = await self.bot.application_info()
        return discord.utils.oauth_url(app_info.id, permissions, scopes=scopes)

    # https://github.com/Kowlin/Sentinel/blob/master/slashinjector/core.py
    def parse_interaction_create(self, data):
        self.bot.dispatch("interaction_create", data)

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if not message.channel.permissions_for(message.guild.me).send_messages:
            return
        if await self.bot.allowed_by_whitelist_blacklist(who=message.author) is False:
            return
        if not re.compile(rf"^<@!?{self.bot.user.id}>$").match(message.content):
            return
        prefixes = await self.bot.get_prefix(message.channel)
        if f"<@!{self.bot.user.id}> " in prefixes:
            prefixes.remove(f"<@!{self.bot.user.id}> ")
        sorted_prefixes = sorted(prefixes, key=len)
        if len(sorted_prefixes) > 500:
            return
        embed = discord.Embed(
            colour=await self.bot.get_embed_colour(message.channel),
            description=f"""
                **Hey there!** <a:bounce:778449468717531166>
                My prefixes in this server are {humanize_list(prefixes)}
                You can type `{sorted_prefixes[0]}help` to view all commands!
                Need some help? Join my [support server!]({SUPPORT_SERVER})
                Looking to invite me? [Click here!]({await self.invite_url()})
            """,
        )
        await message.channel.send(embed=embed)

    @commands.command(hidden=True)
    async def asia(self, ctx):
        """
        RIP ASIA
        """
        await ctx.send(
            "asia is the best person on this earth and loves videos of emo kids dancing"
        )
        await ctx.send(
            "https://cdn.discordapp.com/attachments/768663090337677315/795133511673053225/emokidsyummy.mp4"
        )

    @commands.bot_has_permissions(embed_links=True)
    @commands.command(hidden=True)
    async def maddie(self, ctx):
        """
        Cool Cat :)
        """
        embed = discord.Embed(
            description="maddie is a cool cat + is emotionally attached to this cat’s birthday party :revolving_hearts::revolving_hearts::revolving_hearts::revolving_hearts:",
            color=11985904,
        )
        embed.set_image(
            url="https://cdn.discordapp.com/attachments/768663090337677315/796118254128332820/image0.jpg"
        )
        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def oofchair(self, ctx):
        """
        Cool bot dev
        """
        await ctx.send(
            "oof is p cool :) he's also a bot developer! check out his bot here: http://pwnbot.xyz/"
        )

    @commands.command(aliases=["yt"])
    async def youtube(self, ctx, *, video: str):
        """
        Search for a youtube video.
        Inspired by Aikaterna's YouTube cog
        """
        results = await self.search_youtube(video)
        if results is None:
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
        if results is None:
            await ctx.send("Nothing found.")
            return
        urls = []
        for result in results:
            urls.append(result["info"]["uri"])
        await dpymenu(ctx, urls, timeout=60)

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
        await message.add_reaction("<:idk:838887174345588796")
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
            embed = discord.Embed(color=await ctx.embed_color(), title=t, url = await self.invite_url(), description=d)
            embed.set_footer(text="Note: You need 75 members and 50% of your member count must be human.")
            await ctx.send(embed=embed)
            return

        if not bot.bot:
            await ctx.send("Dumbass")
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
            color=await ctx.embed_color(), title=f"{user.name}'s avatar", description=m
        )
        embed.set_image(url=user.avatar_url_as(size=4096))
        await ctx.send(embed=embed)

    @commands.command()
    async def ping(self, ctx: commands.Context):
        """
        Pong.
        """
        before = time.monotonic()
        msg = await ctx.send("Pong!")
        after = time.monotonic()
        embed = discord.Embed(
            color=await ctx.embed_color(),
            title="Pong!",
            description=(
                f"Websocket Latency: {round(self.bot.latency * 1000, 2)} ms\n"
                f"Message Latency: {round((after - before) * 1000, 2)} ms"
            ),
        )
        try:
            await msg.edit(content=None, embed=embed)
        except discord.NotFound:
            await ctx.send(embed=embed)

    @commands.bot_has_permissions(external_emojis=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["info"])
    async def botinfo(self, ctx: commands.Context):
        """
        Shows info about kaogurai.
        """
        author_repo = "https://github.com/Twentysix26"
        org_repo = "https://github.com/Cog-Creators"
        red_repo = org_repo + "/Red-DiscordBot"
        red_pypi = "https://pypi.org/project/Red-DiscordBot"
        red_server_url = "https://discord.gg/red"
        dpy_repo = "https://github.com/Rapptz/discord.py"
        python_url = "https://www.python.org/"
        kao_repo = "https://github.com/kaogurai/bot"

        dpy_version = "[{}]({})".format(discord.__version__, dpy_repo)
        python_version = "[{}.{}.{}]({})".format(*sys.version_info[:3], python_url)
        red_version = "[{}]({})".format(redbot.__version__, red_pypi)

        about = (
            "This bot is a [custom fork]({}) of [Red, an open source Discord bot]({}) "
            "created by [Twentysix]({}) and [improved by many]({}).\n\n"
            "Red is backed by a passionate community who contributes and "
            "creates content for everyone to enjoy. [Join us today]({}) "
            "and help us improve!\n\n"
            "(c) Cog Creators"
        ).format(kao_repo, red_repo, author_repo, org_repo, red_server_url)
        links = (
            "Click [here]({}) to invite me. You'll need at least 75 members, and 50% of your members must be human.\n\n"
            "If you have any questions, join my [support server]({})"
        ).format(await self.invite_url(), SUPPORT_SERVER)
        embed = discord.Embed(color=(await ctx.embed_colour()))
        embed.add_field(
            name="<:python:817953344118063156> Python", value=python_version
        )
        embed.add_field(
            name="<:discordpy:817952974788624395> discord.py", value=dpy_version
        )
        embed.add_field(name="<:red:230319279424143360> Red", value=red_version)
        embed.add_field(name="About Red", value=about, inline=False)
        embed.add_field(name="Inviting kaogurai", value=links, inline=False)
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
                color=await ctx.embed_color(), title=t, url=first[0].jump_url
            )
            await ctx.send(embed=e)
        else:
            await ctx.send("No messages found.")

    @commands.command()
    async def vowelify(self, ctx: commands.Context, *, text: str):
        """
        Multiplies all vowels in a sentence.
        """
        uwuified = "".join(
            [
                c if c in "aeiouAEIOU" else (c * 3 if c not in "aeiou" else c)
                for c in text
            ]
        )
        await ctx.send(uwuified[:1000])

    @commands.command(aliases=["uwuify", "owo", "owoify"])
    async def uwu(self, ctx: commands.Context, *, text: str):
        """
        Uwuifies a sentence.
        """
        encoded = urllib.parse.quote(text)
        async with self.session.get(
            f"https://owo.l7y.workers.dev/?text={encoded}"
        ) as req:
            if req.status == 200:
                data = await req.text()
                await ctx.send(data[:1000])
            else:
                await ctx.send("Sorry, something went wrong.")

    @commands.command(aliases=["zalgoify"])
    async def zalgo(self, ctx: commands.Context, *, text: str):
        """
        Zalgoifies a sentence.
        """
        t = zalgo.zalgo().zalgofy(text)
        await ctx.send(t[:2000])

    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["ship", "lovecalc"])
    async def lovecalculator(self, ctx, user: discord.User, user2: discord.User = None):
        """
        Calculates the amount of love between you and the bot.
        """
        love = random.randint(0, 100)
        if user2 is None:
            user2 = ctx.author
        ua = user.avatar_url_as(static_format="png")
        u2a = user2.avatar_url_as(static_format="png")
        u = f"https://api.martinebot.com/v1/imagesgen/ship?percent={love}&first_user={ua}&second_user={u2a}&no_69_percent_emoji=false"
        t = f"{user.name} and {user2.name} have {love}% compatibility."
        e = discord.Embed(color=await ctx.embed_color(), title=t)
        e.set_image(url=u)
        e.set_footer(text="Powered by api.martinebot.com")
        await ctx.send(embed=e)

    @commands.command(aliases=["pp", "dingdong"])
    async def penis(self, ctx, *users: discord.Member):
        """
        Get user's penis size!
        """
        if not users:
            users = (ctx.author,)

        penises = {}
        msg = ""
        state = random.getstate()

        for user in users:
            random.seed(user.id)

            dong_size = random.randint(0, 30)

            penises[user] = "8{}D".format("=" * dong_size)

        random.setstate(state)
        dongs = sorted(penises.items(), key=lambda x: x[1])

        for user, dong in dongs:
            msg += "**{}'s size:**\n{}\n".format(user.display_name, dong)

        for page in pagify(msg):
            await ctx.send(page)

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

    @commands.command()
    @commands.is_owner()
    @commands.bot_has_permissions(attach_files=True)
    async def deezerdl(self, ctx, *, song: str):
        """
        Download a song from Deezer.
        """
        tracks = await self.deezerclient.search('track', song)
        if not tracks:
            return await ctx.send("I couldn't find anything for your query.")
        track = tracks[0]
        if int(track["FILESIZE"]) > 8000000:
            return await ctx.send("Sorry, that song is too big to download.")
        title = track["SNG_TITLE"]
        artist = track["ART_NAME"]
        name = f"{artist} - {title}.mp3"
        await ctx.send(f"Downloading {title} by {artist}...")
        async with ctx.typing():
            binary = await self.deezerclient.download(track)
            await ctx.send(file=discord.File(binary, filename=name))

    @commands.command()
    @commands.is_owner()
    @commands.bot_has_permissions(attach_files=True)
    async def deezerplay(self, ctx, *, song: str):
        """
        Play a song from Deezer.
        """
        tracks = await self.deezerclient.search('track', song)
        if not tracks:
            return await ctx.send("I couldn't find anything for your query.")
        track = tracks[0]
        if int(track["FILESIZE"]) > 8000000:
            return await ctx.send("Sorry, that song is too big to download.")
        title = track["SNG_TITLE"]
        artist = track["ART_NAME"]
        await ctx.send(f"Playing {title} by {artist}...")
        async with ctx.typing():
            binary = await self.deezerclient.download(track)
            m = await ctx.send(file=discord.File(binary, filename=f"{title}.mp3"))
        url = m.attachments[0].url
        msg = copy(ctx.message)
        msg.author = ctx.author
        msg.content = ctx.prefix + f"play {url}"

        ctx.bot.dispatch("message", msg)

        





