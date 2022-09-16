import asyncio
import contextlib
import datetime
import random
from io import BytesIO
from typing import Optional
from urllib.parse import quote

import aiohttp
import colorgram
import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from bs4 import BeautifulSoup
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import humanize_list


class AutoAvatar(commands.Cog):
    """
    Sets random bot avatars.
    """

    __version__ = "1.0.1"

    def __init__(self, bot: Red):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.config = Config.get_conf(self, identifier=696969696969494)
        default_global = {
            "current_avatar": "https://discord.com/assets/f9bb9c4af2b9c32a2c5ee0014661546d.png",
            "current_channel": None,
            "weheartit_queries": ["discord"],
            "we_heart_it_cache": ["", "", "", "", "", "", "", "", "", ""],
        }
        self.config.register_global(**default_global)
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(
            self.change_avatar,
            CronTrigger.from_crontab("0 */3 * * *", timezone="America/New_York"),
        )
        self.scheduler.start()

    def cog_unload(self) -> None:
        self.bot.loop.create_task(self.session.close())
        self.scheduler.shutdown()

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx: Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    def get_color(self, avatar: bytes) -> int:
        bio = BytesIO(avatar)
        bio.seek(0)
        colors = colorgram.extract(bio, 1)
        color = colors[0].rgb
        int = (color[0] << 16) + (color[1] << 8) + color[2]  # RGB -> int
        return int

    async def get_we_heart_it_image(self) -> str:
        queries = await self.config.weheartit_queries()
        urls = []
        if queries:
            for query in queries:
                url = f"https://weheartit.com/search/entries?query={quote(query)}"
                urls.append(url)

        links = []
        before_interlaced = []
        for num, url in enumerate(urls):
            async with self.session.get(url) as request:
                if request.status == 200:
                    page = await request.text()
                    soup = BeautifulSoup(page, "html.parser")
                    divs = soup.select("div.entry.grid-item")
                    before_interlaced.append([])
                    for div in divs:
                        link = div.select("img.entry-thumbnail")[0].attrs["src"]
                        better_quality_link = link.replace("superthumb", "original")
                        before_interlaced[num].append(better_quality_link)

        random.shuffle(before_interlaced)
        length_list = []
        for x in before_interlaced:
            length_list.append(len(x))
        length_list.sort(reverse=True)
        if not length_list:
            return 404
        length = length_list[0]
        for x in range(length):
            for y in before_interlaced:
                with contextlib.suppress(IndexError):
                    links.append(y[x])

        if not links:
            return 404

        link = None
        cache = await self.config.we_heart_it_cache()
        for link in links:
            if link not in cache:
                async with self.session.get(link) as request:
                    if request.status == 200:
                        cache.insert(0, link)
                        cache.pop()
                        await self.config.we_heart_it_cache.set(cache)
                        return link

        return random.choice(links)

    async def change_avatar(self, ctx: Optional[Context] = None):
        is_automated = not ctx
        new_avatar = await self.get_we_heart_it_image()
        if new_avatar == 404:
            if not is_automated:
                await ctx.send("No images found for your queries.")
            return
        if not new_avatar:
            if not is_automated:
                await ctx.send("There seems to be issues with weheartit currently.")
            return

        for x in range(5):
            try:
                async with self.session.get(new_avatar) as request:
                    if request.status == 200:
                        avatar = await request.read()
                        break
            except (
                aiohttp.ServerDisconnectedError,
                aiohttp.ServerTimeoutError,
                asyncio.TimeoutError,
            ):
                if x == 4:
                    if not is_automated:
                        await ctx.send(
                            "There seems to be an issue with weheartit currently."
                        )
                    return
                continue

        result = await self.bot.loop.run_in_executor(None, self.get_color, avatar)
        if result:
            self.bot._color = result
            await self.bot._config.color.set(result)

        try:
            await self.bot.user.edit(avatar=avatar)
        except discord.HTTPException:
            return

        if not is_automated:
            await ctx.tick()
        await self.config.current_avatar.set(new_avatar)

        if await self.config.current_channel():
            channel = self.bot.get_channel(await self.config.current_channel())
            if not channel:
                return
            embed = discord.Embed(
                colour=await self.bot.get_embed_colour(channel),
                title="My Current Avatar",
                timestamp=datetime.datetime.utcnow(),
            )
            embed.set_image(url=new_avatar)
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                return

    @commands.group()
    @commands.is_owner()
    async def autoavatar(self, ctx: Context):
        """
        AutoAvatar settings.
        """
        pass

    @autoavatar.command()
    @commands.bot_has_permissions(embed_links=True)
    async def settings(self, ctx: Context):
        """
        Show AutoAvatar settings.
        """
        id = await self.config.current_channel()
        embed = discord.Embed(title="AutoAvatar Settings", colour=await ctx.embed_color())
        qs = await self.config.weheartit_queries()
        if not qs:
            thing = "No Queries"
        else:
            thing = humanize_list(qs)[:1000]

        embed.add_field(name="We Heart It Queries", value=thing)

        ca = await self.config.current_avatar()
        embed.add_field(
            name="Current Avatar",
            value=f"[Click Here]({ca})",
        )
        embed.set_thumbnail(url=ca)
        embed.add_field(name="Current Channel", value=f"<#{id}>" if id else "Disabled")
        await ctx.send(embed=embed)

    @autoavatar.command()
    async def channel(self, ctx: Context, channel: discord.TextChannel = None):
        """
        Sets the channel for the current avatar.
        If no channel is provided, it will clear the set channel.
        """
        if channel is None:
            await self.config.current_channel.set(None)
            await ctx.send("I have cleared the channel.")
        else:
            await self.config.current_channel.set(channel.id)
            await ctx.tick()

    @commands.command()
    @commands.is_owner()
    async def newavatar(self, ctx: Context):
        """
        Changes the bot avatar.
        """
        await self.change_avatar(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def currentavatar(self, ctx: Context):
        """
        Displays the bot's current avatar.
        """
        avatar = await self.config.current_avatar()
        embed = discord.Embed(
            colour=await self.bot.get_embed_colour(ctx.channel),
            title="My Current Avatar",
        )
        embed.set_image(url=avatar)
        await ctx.send(embed=embed)

    @autoavatar.group()
    async def query(self, ctx: Context):
        """
        Set the queries for We Heart It.
        """
        pass

    @query.command(name="add")
    async def query_add(self, ctx: Context, *, query: str):
        """
        Add a query to the list of queries.
        """
        all_queries = await self.config.weheartit_queries()
        if query in all_queries:
            await ctx.send(f"{query} is already in my list of queries.")
            return

        all_queries.append(query)
        await self.config.weheartit_queries.set(all_queries)
        await ctx.tick()

    @query.command(name="remove")
    async def query_remove(self, ctx: Context, *, query: str):
        """
        Remove a query from the list of queries.
        """
        all_queries = await self.config.weheartit_queries()
        if query not in all_queries:
            await ctx.send(f"{query} isn't in my list of queries.")
            return

        all_queries.remove(query)
        await self.config.weheartit_queries.set(all_queries)
        await ctx.tick()
