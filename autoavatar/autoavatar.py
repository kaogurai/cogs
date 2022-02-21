import asyncio
import contextlib
import datetime
import random
import urllib
from io import BytesIO

import aiohttp
import colorgram
import discord
from bs4 import BeautifulSoup
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import humanize_list, pagify

WE_HEART_IT_BASE_URL = "https://weheartit.com"
WE_HEART_IT_QUERY_URL = "https://weheartit.com/search/entries?utf8=✓&ac=0&query={query}"
WE_HEART_IT_QUERY_URL_MOST_POPULAR = (
    "https://weheartit.com/search/entries?query={query}&sort=most_popular"
)


class AutoAvatar(commands.Cog):
    """
    Chooses a random avatar to set from a preset list or can scrape we heart it.
    """

    __version__ = "1.2.3"

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.config = Config.get_conf(self, identifier=696969696969494)
        default_global = {
            "avatars": [],
            "current_avatar": "https://discord.com/assets/f9bb9c4af2b9c32a2c5ee0014661546d.png",
            "current_channel": None,
            "auto_color": False,
            "weheartit": False,
            "weheartit_queries": [],
            "weheartit_query_most_popular": False,
            "we_heart_it_cache": ["", "", "", "", "", "", "", "", "", ""],
        }
        self.config.register_global(**default_global)

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    def get_color(self, avatar):
        bio = BytesIO(avatar)
        bio.seek(0)
        colors = colorgram.extract(bio, 1)
        color = colors[0].rgb
        int = (color[0] << 16) + (color[1] << 8) + color[2]  # RGB -> int
        return int

    async def get_we_heart_it_image(self):
        queries = await self.config.weheartit_queries()
        most_popular = await self.config.weheartit_query_most_popular()
        url = WE_HEART_IT_BASE_URL
        urls = []
        if queries:
            for query in queries:
                if most_popular:
                    url = WE_HEART_IT_QUERY_URL_MOST_POPULAR.format(query=query)
                    urls.append(url)

                else:
                    url = WE_HEART_IT_QUERY_URL.format(query=query)
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

        link = random.choice(links)
        return link

    async def change_avatar(self, ctx):
        all_avatars = await self.config.avatars()
        auto_color = await self.config.auto_color()
        we_heart_it = await self.config.weheartit()

        if we_heart_it:
            new_avatar = await self.get_we_heart_it_image()
            if new_avatar == 404:
                await ctx.send("No images found for your queries.")
                return
            if not new_avatar:
                await ctx.send("There seems to be issues with weheartit currently.")
                return
        else:
            if not all_avatars:
                await ctx.send("You haven't added any avatars yet.")
                return

            new_avatar = random.choice(all_avatars)

        for x in range(5):
            try:
                async with self.session.get(new_avatar) as request:
                    if request.status == 200:
                        avatar = await request.read()
                        break
                    else:
                        if not we_heart_it:
                            all_avatars.remove(new_avatar)
                            await self.config.avatars.set(all_avatars)
                        return
            except (
                aiohttp.ServerDisconnectedError,
                aiohttp.ServerTimeoutError,
                asyncio.TimeoutError,
            ):
                if x == 4:
                    if we_heart_it:
                        await ctx.send(
                            "There seems to be an issue with weheartit currently."
                        )
                    else:
                        await ctx.send(
                            "There seems to be an issue trying to download an avatar."
                        )
                    return
                continue

        if auto_color:
            result = await self.bot.loop.run_in_executor(None, self.get_color, avatar)
            if result:
                ctx.bot._color = result
                await ctx.bot._config.color.set(result)

        try:
            await self.bot.user.edit(avatar=avatar)
        except discord.HTTPException:
            return
        except discord.InvalidArgument:
            all_avatars.remove(new_avatar)
            await self.config.avatars.set(all_avatars)
            return

        await ctx.tick()
        await self.config.current_avatar.set(new_avatar)

        if await self.config.current_channel():
            channel = self.bot.get_channel(await self.config.current_channel())
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
    async def autoavatar(self, ctx):
        """
        AutoAvatar settings.
        """
        pass

    @autoavatar.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.is_owner()
    async def settings(self, ctx):
        """
        Show AutoAvatar settings.
        """
        id = await self.config.current_channel()
        whi = await self.config.weheartit()
        embed = discord.Embed(title="AutoAvatar Settings", colour=await ctx.embed_color())
        embed.add_field(
            name="Auto Color",
            value="Enabled" if await self.config.auto_color() else "Disabled",
        )
        embed.add_field(
            name="We Heart It",
            value="Enabled" if whi else "Disabled",
        )
        if whi:
            qs = await self.config.weheartit_queries()
            if not qs:
                thing = "None"
            else:
                for q in qs:
                    qs.remove(q)
                    nqs = urllib.parse.unquote(q)
                    qs.append(nqs)
                    thing = humanize_list(qs)[:500]
            embed.add_field(name="We Heart It Queries", value=thing)
            v = "Recent Images"
            mp = await self.config.weheartit_query_most_popular()
            if mp:
                v = "Popular Images"

            embed.add_field(name="We Heart It Type", value=v)
        ca = await self.config.current_avatar()
        embed.add_field(
            name="Current Avatar",
            value=f"[Click Here]({ca})",
        )
        embed.set_thumbnail(url=ca)
        embed.add_field(
            name="Avatars Added",
            value=f"{len(await self.config.avatars())} (disabled)"
            if whi
            else len(await self.config.avatars()),
        )
        embed.add_field(name="Current Channel", value=f"<#{id}>" if id else "Disabled")
        await ctx.send(embed=embed)

    @autoavatar.command()
    @commands.is_owner()
    async def channel(self, ctx, channel: discord.TextChannel = None):
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

    @autoavatar.command(name="add")
    @commands.is_owner()
    async def avatar_add(self, ctx, *links: str):
        """
        Adds avatar links.
        """
        all_avatars = await self.config.avatars()

        for link in links:
            try:
                async with self.session.get(link) as r:
                    if r.status != 200:
                        await ctx.send(f"{link[:1000]} is not a valid link.")
                        continue
            except Exception:
                await ctx.send(f"{link[:1000]} is not a valid link.")
                continue

            if link not in all_avatars:
                all_avatars.append(link)
            else:
                await ctx.send(
                    f"{link:1000} was already in my list of avatars, did you mean to remove it?"
                )
        await self.config.avatars.set(all_avatars)
        await ctx.tick()

    @autoavatar.command(name="remove")
    @commands.is_owner()
    async def avatar_remove(self, ctx, *links: str):
        """
        Removes an avatar link.
        """
        all_avatars = await self.config.avatars()

        for link in links:
            if link in all_avatars:
                all_avatars.remove(link)
            else:
                await ctx.send(
                    f"{link} wasn't in my list of avatars, did you mean to add it?"
                )
        await self.config.avatars.set(all_avatars)
        await ctx.tick()

    @autoavatar.command(name="list")
    @commands.is_owner()
    async def avatar_list(self, ctx):
        """
        Lists all bot avatars.
        """
        all_avatars = await self.config.avatars()

        if not all_avatars:
            await ctx.send("I do not have any avatars saved.")
            return

        origin = ""

        for link in all_avatars:
            toappend = "<" + link + ">" + "\n"
            origin += toappend

        pages = [p for p in pagify(text=origin, delims="\n")]

        for page in pages:
            await ctx.author.send(page)

    @commands.command()
    @commands.is_owner()
    async def newavatar(self, ctx):
        """
        Changes the bot avatar.
        """
        await self.change_avatar(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def currentavatar(self, ctx):
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

    @autoavatar.command()
    @commands.is_owner()
    async def color(self, ctx):
        """
        Toggle if the embed color is based on the avatar's color.
        """
        auto_color = await self.config.auto_color()
        await self.config.auto_color.set(not auto_color)
        await ctx.send(
            f"The embed color is now {'automatic' if not auto_color else 'manual'}."
        )

    @autoavatar.group()
    @commands.is_owner()
    async def weheartit(self, ctx):
        """
        Settings to use We Heart It.
        """
        pass

    @weheartit.command()
    async def toggle(self, ctx):
        """
        Toggle if the bot uses We Heart It for new avatars.
        """
        weheartit = await self.config.weheartit()
        new = not weheartit
        if new:
            await self.config.weheartit.set(True)
            await ctx.send("I will now use weheartit for new avatars.")
        else:
            await self.config.weheartit.set(False)
            await ctx.send("I will no longer use weheartit for new avatars.")

    @weheartit.command()
    async def mostpopular(self, ctx):
        """
        Set the most popular avatar.
        """
        popular = await self.config.weheartit_most_popular()
        new = not popular
        if new:
            await self.config.weheartit_most_popular.set(True)
            m = (
                "I will now use the most popular avatars from your queries on We Heart It. "
                "Keep in mind you will get better quality images, but they will repeat extremely often."
            )
            await ctx.send(m)
        else:
            await self.config.weheartit_most_popular.set(False)
            await ctx.send(
                "I will now use recent images from your query on We Heart It. "
            )

    @weheartit.group()
    async def query(self, ctx):
        """
        Set the queries for We Heart It.
        """
        pass

    @query.command(name="add")
    async def query_add(self, ctx, *, query: str):
        """
        Add a query to the list of queries.
        """
        all_queries = await self.config.weheartit_queries()
        nquery = urllib.parse.quote_plus(query)
        if nquery in all_queries:
            await ctx.send(f"{query} is already in my list of queries.")
            return

        all_queries.append(nquery[:1024])
        await self.config.weheartit_queries.set(all_queries)
        await ctx.tick()

    @query.command(name="remove")
    async def query_remove(self, ctx, *, query: str):
        """
        Remove a query from the list of queries.
        """
        all_queries = await self.config.weheartit_queries()
        nquery = urllib.parse.quote_plus(query)
        if nquery not in all_queries:
            await ctx.send(f"{query} isn't in my list of queries.")
            return

        all_queries.remove(nquery)
        await self.config.weheartit_queries.set(all_queries)
        await ctx.tick()
