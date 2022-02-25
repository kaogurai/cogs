import asyncio
import datetime
import urllib
from io import BytesIO

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .abc import MixinMeta


class MediaMixin(MixinMeta):
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
                    await ctx.send("That's not a valid option.")
                    return

                async with self.session.get(audio["url"]) as resp:
                    if resp.status != 200:
                        await ctx.send(
                            "Something went wrong when trying to get the song. Please try again later."
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
                        description=f"That song is too big to send in this guild. Click [here]({audio['url']}) to download it.",
                        url=audio["url"],
                    )
                    await ctx.send(embed=embed)
                else:
                    biof = BytesIO(data)
                    biof.seek(0)
                    await ctx.send(
                        file=discord.File(biof, filename=f"{audio['tit_art']}.mp3")
                    )

    async def get_omdb_info(self, type, query):
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
    async def movie(self, ctx, *, movie: str):
        """
        Get information about a specific movie.
        """
        data = await self.get_omdb_info("movie", movie)
        if not data:
            await ctx.send("I couldn't find that movie!")
            return

        embed = discord.Embed(color=await ctx.embed_color(), title=data["Title"])
        if data["Website"] != "N/A":
            embed.url = data["Website"]
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
        embed.add_field(name="Plot", value=data["Plot"], inline=False)

        await ctx.send(embed=embed)

    @commands.command(aliases=["tv", "tvshow", "tvseries", "series"])
    @commands.bot_has_permissions(embed_links=True)
    async def show(self, ctx, *, show: str):
        """
        Get information about a specific show.
        """
        data = await self.get_omdb_info("series", show)
        if not data:
            await ctx.send("I couldn't find that show!")
            return
        print(data)

        embed = discord.Embed(color=await ctx.embed_color(), title=data["Title"])
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
        embed.add_field(name="Plot", value=data["Plot"], inline=False)

        await ctx.send(embed=embed)
