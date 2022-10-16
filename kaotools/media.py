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
    @commands.command(aliases=["dl", "musicdl", "musicdownload"])
    @commands.bot_has_permissions(attach_files=True, add_reactions=True, embed_links=True)
    async def download(self, ctx: Context, *, song: str):
        """
        Download a song from Deezer.

        The files are returned in 128kbps MP3 format.
        """
        async with ctx.typing():
            async with self.session.get(
                "http://zeus:9999/v1/search", params={"query": song}
            ) as resp:
                if resp.status != 200:
                    await ctx.send("Something went wrong when trying to search.")
                    return
                data = await resp.json(content_type=None)
            tracks = data["tracks"]
            if not tracks:
                await ctx.send("No results found.")
                return

            msg = ""
            for i, track in enumerate(tracks):
                msg += f"{i + 1}. {track['name']} - {track['artist']['name']} ({datetime.timedelta(seconds=track['duration'])})\n"

            pages = [p for p in pagify(text=msg, delims="\n", page_length=512)]
            embeds = []

            for i, msg in enumerate(pages):
                embed = discord.Embed(
                    title="Which song do you want to download?",
                    description=msg,
                    color=await ctx.embed_color(),
                )
                footer = "Type the number of the song you want to download."
                if len(pages) > 1:
                    footer += f" | Page {i + 1}/{len(pages)}"
                embed.set_footer(text=footer)
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
            else:
                try:
                    track = tracks[int(msg.content) - 1]
                except (IndexError, ValueError):
                    await ctx.send("Invalid number.")
                    return

            async with self.session.get(
                f"http://zeus:9999/v1/track/download/{track['id']}"
            ) as resp:
                if resp.status != 200:
                    await ctx.send(
                        "Something went wrong when trying to download the song."
                    )
                    return
                res = await resp.read()

            if ctx.guild:
                limit = ctx.guild.filesize_limit
            else:
                limit = 8000000

            if len(res) > limit:
                await ctx.send(
                    "The file is too big to be sent here. Try in a server with a bigger limit."
                )
                return

            bfile = BytesIO(res)
            bfile.seek(0)
            await ctx.send(
                file=discord.File(
                    bfile, filename=f"{track['name']} - {track['artist']['name']}.mp3"
                )
            )

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
