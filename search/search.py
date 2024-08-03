from typing import List, Optional, Tuple

import aiohttp
import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

QWANT_API_BASE = "https://api.qwant.com/v3"


class Search(commands.Cog):
    """
    Search the web, from Discord.
    """

    __version__ = "2.0.2"

    def __init__(self, bot: Red):
        """
        Initalizes the cog by creating an HTTP session with the correct headers.
        """
        self.bot = bot
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36"
            }
        )

    async def red_delete_data_for_user(self, **kwargs):
        """
        This cog does not store user data.
        """
        return

    def format_help_for_context(self, ctx: Context):
        """
        Adds the cog version to the help menu.
        """
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def _search_qwant(
        self,
        ctx: Context,
        type: str,
        count: int,
        query: str,
    ) -> Optional[Tuple[Optional[str], List[dict]]]:
        """
        Search Qwant for something.
        """
        safesearch = 0 if ctx.channel.is_nsfw() or ctx.guild is None else 1
        params = {
            "q": query,
            "count": count,
            "offset": 0,
            "safesearch": safesearch,
            "locale": "en_US",
            "device": "desktop",
            "t": type,
        }
        async with self.session.get(
            QWANT_API_BASE + "/search/" + type, params=params
        ) as resp:
            if resp.status != 200:
                return None, None
            data = await resp.json()
            _items = data["data"]["result"]["items"]
            items = _items
            sidebar = None

            if type == "web":

                items = {}
                for result in _items["mainline"]:
                    if result["type"] == type:
                        items = result["items"]  # Filters out ads

                for result in _items["sidebar"]:
                    if result["type"] == "ia/knowledge":
                        sidebar = result["endpoint"]

            return sidebar, items

    @commands.command(aliases=["google"])
    @commands.bot_has_permissions(embed_links=True)
    async def websearch(self, ctx: Context, *, query: str):
        """
        Search for something on the web.

        SafeSearch will be disabled in NSFW channels.
        """
        sidebar, results = await self._search_qwant(ctx, "web", 10, query)
        if not results:
            await ctx.send("No results found.")
            return

        if sidebar:
            async with self.session.get(QWANT_API_BASE + sidebar) as resp:
                if resp.status == 200:
                    sidebar = (await resp.json())["data"]["result"]

        embeds = []

        # Max amount of items in results is 10
        # We want to show 3 results per page
        for i in range(0, 10, 3):
            embed = discord.Embed(
                title=f"Search Results for {query[:50] + '...' if len(query) > 50 else query}",
                color=await ctx.embed_color(),
            )
            # Add sidebar if it exists, only on first page
            if sidebar and i == 0:
                embed.add_field(
                    name="Info Box - " + sidebar["title"],
                    value=f"{sidebar['url']}\n{sidebar['description']}",
                    inline=False,
                )
                if sidebar["thumbnail"]["portrait"]:
                    embed.set_thumbnail(url=sidebar["thumbnail"]["portrait"])

            for result in results[i : i + 3]:
                embed.add_field(
                    name=result["title"],
                    value=f"{result['url']}\n{result['desc']}",
                    inline=False,
                )

            embed.set_footer(text=f"Page {i // 3 + 1}/{len(results) // 3 + 1}")

            embeds.append(embed)

        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @commands.command(aliases=["imgsearch", "img", "image"])
    @commands.bot_has_permissions(embed_links=True)
    async def imagesearch(self, ctx: Context, *, query: str):
        """
        Search for images on the web.

        SafeSearch will be disabled in NSFW channels.
        """
        _, results = await self._search_qwant(ctx, "images", 50, query)
        if not results:
            await ctx.send("No results found.")
            return

        embeds = []
        for i, result in enumerate(results):
            embed = discord.Embed(
                title=result["title"], color=await ctx.embed_color(), url=result["url"]
            )
            embed.set_image(url=result["media"])
            embed.set_footer(text=f"Image {i + 1}/{len(results)}")
            embeds.append(embed)

        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @commands.command(aliases=["vidsearch", "vid", "video"])
    @commands.bot_has_permissions(embed_links=True)
    async def videosearch(self, ctx: Context, *, query: str):
        """
        Search for videos on the web.

        SafeSearch will be disabled in NSFW channels.
        """
        _, results = await self._search_qwant(ctx, "videos", 10, query)
        if not results:
            await ctx.send("No results found.")
            return

        embeds = []
        for i, result in enumerate(results):
            embed = discord.Embed(
                title=result["title"], color=await ctx.embed_color(), url=result["url"]
            )
            embed.set_image(url=result["thumbnail"])
            embed.set_footer(text=f"Video {i + 1}/{len(results)}")
            embeds.append(embed)

        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @commands.command(aliases=["newsearch", "news"])
    @commands.bot_has_permissions(embed_links=True)
    async def newssearch(self, ctx: Context, *, query: str):
        """
        Search for news on the web.
        """
        _, results = await self._search_qwant(ctx, "news", 10, query)
        if not results:
            await ctx.send("No results found.")
            return

        embeds = []

        # Max amount of items in results is 10
        # We want to show 5 results per page
        for i in range(0, 10, 3):
            embed = discord.Embed(
                title=f"News for {query[:50] + '...' if len(query) > 50 else query}",
                color=await ctx.embed_color(),
            )
            for result in results[i : i + 3]:
                embed.add_field(
                    name=result["title"]
                    + " - "
                    + (result["press_name"] or result["domain"]),
                    value=f"{result['url']}\n{result['desc']}",
                    inline=False,
                )

            embed.set_footer(text=f"Page {i // 3 + 1}/{len(results) // 3 + 1}")

            embeds.append(embed)

        await menu(ctx, embeds, DEFAULT_CONTROLS)
