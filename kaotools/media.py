import asyncio
import datetime
from io import BytesIO

import discord
from redbot.core import commands
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .abc import MixinMeta


class MediaMixin(MixinMeta):

    async def get_omdb_info(self, type: str, query: str) -> dict:
        params = {"apikey": self.omdb_key, "type": type, "t": query}
        async with self.session.get("http://www.omdbapi.com/", params=params) as req:
            if req.status != 200:
                return
            data = await req.json()
            if data["Response"] != "True":
                return
            return data

    @commands.command(aliases=["film"])
    @commands.bot_has_permissions(embed_links=True)
    async def movie(self, ctx: Context, *, movie: str):
        """
        Get information about a specific movie.
        """
        data = await self.get_omdb_info("movie", movie)
        if not data:
            await ctx.send("I couldn't find that movie!")
            return

        embed = discord.Embed(
            color=await ctx.embed_color(), title=data["Title"], description=data["Plot"]
        )
        if data["Website"] != "N/A":
            embed.url = data["Website"]
        if data["Poster"] != "N/A":
            embed.set_thumbnail(url=data["Poster"])
        embed.add_field(name="Year", value=data["Year"])
        embed.add_field(name="Rated", value=data["Rated"])
        embed.add_field(name="Runtime", value=data["Runtime"])
        embed.add_field(name="Genre", value=data["Genre"])
        embed.add_field(name="Director", value=data["Director"])
        embed.add_field(name="Country", value=data["Country"])
        embed.add_field(name="Awards", value=data["Awards"])
        embed.add_field(name="Metascore", value=data["Metascore"])
        embed.add_field(name="IMDB Rating", value=data["imdbRating"])
        embed.add_field(name="IMDB Votes", value=data["imdbVotes"])
        embed.add_field(name="IMDB ID", value=data["imdbID"])
        embed.add_field(name="Actors", value=data["Actors"])
        embed.add_field(name="Languages", value=data["Language"])

        await ctx.send(embed=embed)

    @commands.command(aliases=["tv", "tvshow", "tvseries", "series"])
    @commands.bot_has_permissions(embed_links=True)
    async def show(self, ctx: Context, *, show: str):
        """
        Get information about a specific show.
        """
        data = await self.get_omdb_info("series", show)
        if not data:
            await ctx.send("I couldn't find that show!")
            return

        embed = discord.Embed(
            color=await ctx.embed_color(), title=data["Title"], description=data["Plot"]
        )
        if data["Poster"] != "N/A":
            embed.set_thumbnail(url=data["Poster"])
        embed.add_field(name="Year", value=data["Year"])
        embed.add_field(name="Rated", value=data["Rated"])
        embed.add_field(name="Runtime", value=data["Runtime"])
        embed.add_field(name="Genre", value=data["Genre"])
        embed.add_field(name="Director", value=data["Director"])
        embed.add_field(name="Country", value=data["Country"])
        embed.add_field(name="Awards", value=data["Awards"])
        embed.add_field(name="Metascore", value=data["Metascore"])
        embed.add_field(name="IMDB Rating", value=data["imdbRating"])
        embed.add_field(name="IMDB Votes", value=data["imdbVotes"])
        embed.add_field(name="IMDB ID", value=data["imdbID"])
        embed.add_field(name="Actors", value=data["Actors"])
        embed.add_field(name="Languages", value=data["Language"])

        await ctx.send(embed=embed)
