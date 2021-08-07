import asyncio
import io
import random
import re
import sys
import time

import aiohttp
import discord
import pyppeteer
import redbot
from pyppeteer import launch
from redbot.core import commands
from redbot.core.utils._dpy_menus_utils import dpymenu
from redbot.core.utils.chat_formatting import humanize_list

SUPPORT_SERVER = "https://discord.gg/p6ehU9qhg8"


class KaoTools(commands.Cog):
    """Random tools for kaogurai that fit nowhere else."""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        setattr(bot._connection, "parse_interaction_create", self.parse_interaction_create)
        bot._connection.parsers["INTERACTION_CREATE"] = self.parse_interaction_create

    def cog_unload(self):
        del self.bot._connection.parsers["INTERACTION_CREATE"]
        self.bot.loop.create_task(self.session.close())

    async def search_youtube(self, query):
        """Make a Get call to FAKE youtube data api (HEHE)."""
        params = {"identifier": "ytsearch:" + query}
        headers = {"Authorization": "youshallnotpass", "Accept": "application/json"}
        async with self.session.get(
            "http://localhost:2333/loadtracks", params=params, headers=headers
        ) as request:
            if request.status == 200:
                response = await request.json()
                try:
                    return response["tracks"]
                except:
                    return None

    async def invite_url(self, snowflake: int = None) -> str:
        """
        Generates the invite URL for the bot.

        Returns
        -------
        str
            Invite URL.
        """
        scopes = ("bot", "applications.commands")
        data = await self.bot._config.all()
        perms_int = data["invite_perm"]
        permissions = discord.Permissions(perms_int)
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

    @commands.command()
    async def debugerror(self, ctx, error_code: str):
        """Fetches error code information from hastebin."""
        async with self.session.get(
            f"https://haste.kaogurai.xyz/raw/{error_code}"
        ) as request:
            txt = await request.text()
            if len(txt) > 4000:
                txt = txt[:4000]
            embed = discord.Embed(color=await ctx.embed_color())
            embed.description = f"```yaml\n{txt}```"
            embed.set_footer(text=f"Error Code: {error_code}")
            await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def asia(self, ctx):
        """Emo kids lover"""
        await ctx.send(
            "asia is the best person on this earth and loves videos of emo kids dancing"
        )
        await ctx.send(
            "https://cdn.discordapp.com/attachments/768663090337677315/795133511673053225/emokidsyummy.mp4"
        )

    @commands.bot_has_permissions(embed_links=True)
    @commands.command(hidden=True)
    async def maddie(self, ctx):
        """Cool Cat :)"""
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
        """Cool bot dev"""
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
        """Create a simple poll."""
        if len(question) > 2000:
            await ctx.send("That question is too long.")
            return
        message = await ctx.send(f"**{ctx.author} asks:** " + question)
        await message.add_reaction("👍")
        await message.add_reaction("<:idk:838887174345588796")
        await message.add_reaction("👎")

    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["support", "inv"])
    async def invite(self, ctx, bot: discord.User = None):
        """Invite me or another bot!"""
        if bot is None:
            embed = discord.Embed(
                title="Thanks for using me!",
                color=await ctx.embed_color(),
                url="https://kaogurai.xyz",
            )
            embed.set_thumbnail(url=ctx.me.avatar_url)
            embed.add_field(
                name="Bot Invite",
                value=(f"[Click Here]({await self.invite_url()})"),
                inline=True,
            )
            embed.add_field(
                name="Support Server",
                value="[Click Here](https://discord.gg/p6ehU9qhg8)",
                inline=True,
            )
            await ctx.send(embed=embed)
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
        """Get the current amount of members in the server."""
        count = len(ctx.guild.members)
        await ctx.send(f"There are currently **{count}** members in this server.")

    @commands.command(aliases=["someone", "pickuser", "randommember", "picksomeone"])
    @commands.guild_only()
    async def randomuser(self, ctx):
        """Pick a random user in the server."""
        await ctx.send(f"<@{random.choice(ctx.guild.members).id}>")

    @commands.command(aliases=["colour"])
    @commands.bot_has_permissions(embed_links=True)
    async def color(self, ctx, color: discord.Colour):
        """View information and a preview of a color."""
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
        """Get a user's avatar."""
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
        Shows info about [botname].
        """
        author_repo = "https://github.com/Twentysix26"
        org_repo = "https://github.com/Cog-Creators"
        red_repo = org_repo + "/Red-DiscordBot"
        red_pypi = "https://pypi.org/project/Red-DiscordBot"
        red_server_url = "https://discord.gg/red"
        dpy_repo = "https://github.com/Rapptz/discord.py"
        python_url = "https://www.python.org/"

        dpy_version = "[{}]({})".format(discord.__version__, dpy_repo)
        python_version = "[{}.{}.{}]({})".format(*sys.version_info[:3], python_url)
        red_version = "[{}]({})".format(redbot.__version__, red_pypi)

        about = (
            "This bot is a custom fork of [Red, an open source Discord bot]({}) "
            "created by [Twentysix]({}) and [improved by many]({}).\n\n"
            "Red is backed by a passionate community who contributes and "
            "creates content for everyone to enjoy. [Join us today]({}) "
            "and help us improve!\n\n"
            "(c) Cog Creators"
        ).format(red_repo, author_repo, org_repo, red_server_url)
        links = (
            "If you're looking to invite me, [click here.]({})\n"
            "If you're looking for support or have any questions, [click here.]({})"
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
        embed.add_field(name="Quick Links", value=links, inline=False)
        await ctx.send(embed=embed)

    @commands.bot_has_permissions(attach_files=True)
    @commands.command(aliases=["ss"])
    @commands.is_owner()
    async def screenshot(self, ctx, link: str, wait: int = 3):
        """
        Screenshots a given link.
        If no time is given, it will wait 3 seconds to screenshot
        """

        await ctx.trigger_typing()
        browser = await launch()
        page = await browser.newPage()
        await page.setViewport({"width": 1280, "height": 720})
        try:
            await page.goto(link)
        except pyppeteer.page.PageError:
            await ctx.send("Sorry, I couldn't find anything at that link!")
            await browser.close()
            return
        except Exception:
            await ctx.send(
                "Sorry, I ran into an issue! Make sure to include http:// or https:// at the beginning of the link."
            )
            await browser.close()
            return

        await asyncio.sleep(wait)
        result = await page.screenshot()
        await browser.close()
        f = io.BytesIO(result)
        file = discord.File(f, filename="screenshot.png")
        await ctx.send(file=file)
