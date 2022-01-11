import contextlib
import random
import re
import urllib
from copy import copy

import aiohttp
import discord
from redbot.cogs.downloader.converters import InstalledCog
from redbot.core import Config, commands
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import box, humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from zalgo_text import zalgo

from .deezer import Deezer

SUPPORT_SERVER = "https://discord.gg/p6ehU9qhg8"


class KaoTools(commands.Cog):
    """
    Random things that make kaogurai kaogurai.
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
        self.deezerclient = Deezer()
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
        d = (
            "**Hey there!**\n"
            f"My prefixes in this server are {humanize_list(prefixes)}\n"
            f"You can type `{sorted_prefixes[0]}help` to view all commands!\n"
        )
        embed = discord.Embed(
            colour=await self.bot.get_embed_colour(message.channel), description=d
        )
        await message.channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """
        Leave guilds in the blacklist
        Leave guilds with less than 50 members
        Leave guilds with more than 50% bots
        Don't leave guilds in the whitelist
        """
        if not guild:
            return
        if guild.id in await self.config.whitelist():
            return
        if guild.id in await self.config.blacklist():
            await guild.leave()
            return
        botcount = len([x async for x in AsyncIter(guild.members) if x.bot])
        if guild.member_count < 50 or botcount / guild.member_count > 0.5:
            if hasattr(guild, "system_channel") and guild.system_channel:
                with contextlib.suppress(discord.Forbidden):
                    m = (
                        "I'm leaving this server because it doesn't meet my requirements.\n\n"
                        "Remember:\n"
                        "1. Your server needs more at least 50 members\n"
                        "2. You can't have more than 50% of your members be bots"
                    )
                    embed = discord.Embed(
                        title="Hey there!",
                        color=await self.bot.get_embed_colour(guild.system_channel),
                        description=m,
                    )
                    await guild.system_channel.send(embed=embed)
            await guild.leave()
            return

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

    @commands.command()
    async def vowelify(self, ctx: commands.Context, *, text: str):
        """
        Multiplies all vowels in a sentence.
        """
        uwuified = "".join(
            [c if c in "aeiouAEIOU" else (c * 3 if c not in "aeiou" else c) for c in text]
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
        tracks = await self.deezerclient.search("track", song)
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
            await ctx.send(file=discord.File(fp=binary, filename=name))

    @commands.command()
    @commands.is_owner()
    @commands.bot_has_permissions(attach_files=True)
    async def deezerplay(self, ctx, *, song: str):
        """
        Play a song from Deezer.
        """
        tracks = await self.deezerclient.search("track", song)
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
            m = await ctx.send(file=discord.File(fp=binary, filename=f"{title}.mp3"))
        url = m.attachments[0].url
        msg = copy(ctx.message)
        msg.author = ctx.author
        msg.content = ctx.prefix + f"play {url}"

        ctx.bot.dispatch("message", msg)

    @commands.is_owner()
    @commands.group(aliases=["guildmgr"])
    async def guildmanager(self, ctx):
        """
        Manage bot guilds.
        """

    @guildmanager.command()
    async def whitelist(self, ctx, id: int = None):
        """
        Whitelist a guild or remove a guild from the whitelist.

        The whitelist will be listed if no guild is provided
        """
        list = await self.config.whitelist()
        if not id and not list:
            return await ctx.send("There are no guilds on the whitelist.")
        if not id:
            string = "Whitelisted Guilds:\n"
            for guild in list:
                string += f"{guild}\n"
            for page in pagify(string, delims=["\n"]):
                await ctx.send(page)
            return
        if id in list:
            list.remove(id)
            await self.config.whitelist.set(list)
            await ctx.send(f"Removed {id} from the whitelist.")
            return
        list.append(id)
        await self.config.whitelist.set(list)
        await ctx.send(f"Added {id} to the whitelist.")

    @guildmanager.command()
    async def blacklist(self, ctx, id: int = None):
        """
        Blacklist a guild or remove a guild from the whitelist.

        The blacklist will be listed if no guild is provided
        """
        list = await self.config.blacklist()
        if not id and not list:
            return await ctx.send("There are no guilds on the blacklist.")
        if not id:
            string = "Blacklisted Guilds:\n"
            for guild in list:
                string += f"{guild}\n"
            for page in pagify(string, delims=["\n"]):
                await ctx.send(page)
            return
        if id in list:
            list.remove(id)
            await self.config.whitelist.set(list)
            await ctx.send(f"Removed {id} from the blacklist.")
            return
        list.append(id)
        await self.config.whitelist.set(list)
        await ctx.send(f"Added {id} to the blacklist.")

    @commands.is_owner()
    @commands.command()
    async def updr(self, ctx, *cogs: InstalledCog):
        """Update cogs without questioning about reload."""
        ctx.assume_yes = True
        cog_update_command = ctx.bot.get_command("cog update")
        if not cog_update_command:
            await ctx.send(f"I can't find `{ctx.prefix}cog update` command")
            return
        await ctx.invoke(cog_update_command, *cogs)

    @commands.command()
    @commands.is_owner()
    async def unusedrepos(self, ctx):
        """View unused downloader repos."""
        repo_cog = self.bot.get_cog("Downloader")
        if not repo_cog:
            return await ctx.send("Downloader cog not found.")
        repos = [r.name for r in repo_cog._repo_manager.repos]
        active_repos = {c.repo_name for c in await repo_cog.installed_cogs()}
        for r in active_repos:
            try:
                repos.remove(r)
            except:
                pass
        if not repos:
            await ctx.send("All repos are currently being used!")
            return
        await ctx.send(f"Unused: \n" + box(repos, lang="py"))

    @commands.command(aliases=["definition", "def", "synonym", "antonym"])
    async def define(self, ctx, *, thing_to_define):
        """Define a word or phrase."""
        url_encoded = urllib.parse.quote(thing_to_define)
        url = "https://api.dictionaryapi.dev/api/v2/entries/en/{url_encoded}"
        async with self.session.get(url.format(url_encoded=url_encoded)) as resp:
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
            embed.title = f"{result['word']} ({result['meanings'][0]['partOfSpeech']})"
            embed.description = result['meanings'][0]['definitions'][0]["definition"]
            if 'example' in result['meanings'][0]['definitions'][0]:
                embed.add_field(name="Example", value=result['meanings'][0]['definitions'][0]["example"])
            if result['meanings'][0]['definitions'][0]["synonyms"]:
                embed.add_field(name="Synonyms", value=", ".join(result['meanings'][0]['definitions'][0]["synonyms"]))
            if result['meanings'][0]['definitions'][0]["antonyms"]:
                embed.add_field(name="Antonyms", value=", ".join(result['meanings'][0]['definitions'][0]["antonyms"]))
            if len(data) > 1:
                embed.set_footer(text=f"Result {i + 1}/{len(data)}")
            embeds.append(embed)
        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            await menu(ctx, embeds, DEFAULT_CONTROLS)
