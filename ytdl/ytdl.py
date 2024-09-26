import asyncio
import contextlib
import io
import random
import re
import string
from typing import Coroutine, Optional, Tuple

import aiohttp
import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import Context

INVIDIOUS_DOMAIN = "yt.drgnz.club"


class YTDL(commands.Cog):
    """
    Downloads YouTube videos.
    """

    __version__ = "2.1.0"

    def __init__(self, bot: Red):
        """
        Initializes the cog by setting up the HTTP session with the correct
        headers and compiling the YouTube regex.
        """
        self.bot = bot
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36"
            }
        )
        self.youtube_regex = re.compile(
            r"(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?(?P<id>[A-Za-z0-9\-=_]{11})"
        )

    async def red_delete_data_for_user(self, **kwargs) -> None:
        """
        This cog does not store any user data.
        """
        return

    def format_help_for_context(self, ctx: Context) -> None:
        """
        Adds the cog version to the help menu.
        """
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    def _extract_video_id(self, url: str) -> Optional[str]:
        """
        Extracts the video ID from a YouTube URL.
        """
        match = self.youtube_regex.search(url)
        if match:
            return match["id"]

    async def _get_video_info(self, video_id: str) -> Optional[dict]:
        """
        Gets the video info from the Invidious API.
        """
        async with self.session.get(
            f"https://{INVIDIOUS_DOMAIN}/api/v1/videos/{video_id}"
        ) as response:
            if response.status == 200:
                return await response.json()

    async def _shorten_url(self, url: str) -> Optional[str]:
        """
        Returns a shortened version of a URL using the Ulvis API.
        """
        base_url = "https://ulvis.net/API/write/get"
        params = {
            "url": url,
            "type": "json",  # We want the response in JSON format
        }
        async with self.session.get(base_url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("success"):
                    return data["data"]["url"]

    async def _injector(
        self, data: dict, coro: Coroutine
    ) -> Tuple[dict, Optional[str]]:
        return data, await coro

    async def _fix_urls(self, data: dict) -> dict:
        things = []

        for video_format in data["adaptiveFormats"]:
            func = self._shorten_url(video_format["url"])
            things.append(self._injector(video_format, func))

        for video_format in data["formatStreams"]:
            func = self._shorten_url(video_format["url"])
            things.append(self._injector(video_format, func))

        results = await asyncio.gather(*things)

        for video_data, url_data in results:
            if url_data:
                video_data["shortened_url"] = url_data

        return data

    @commands.command(aliases=["youtubedownload"])
    @commands.bot_has_permissions(embed_links=True)
    async def ytdl(self, ctx: Context, url: str):
        """
        Download a video from YouTube.
        """
        async with ctx.typing():
            video_id = self._extract_video_id(url)
            if not video_id:
                await ctx.send("That is not a valid YouTube URL.")
                return

            video_info = await self._get_video_info(video_id)
            if not video_info:
                await ctx.send("Something went wrong.")
                return

            embed = discord.Embed(
                title=video_info["title"],
                url=url,
                color=await ctx.embed_color(),
            )
            embed.set_thumbnail(url=video_info["videoThumbnails"][-1]["url"])
            embed.set_footer(
                text=f"Type the number of the file(s) you want to download. If you want more than one, separate them with a comma."
            )

            video_info = await self._fix_urls(video_info)

            urls = []

            regular_formats = ""

            for video_format in video_info["formatStreams"]:
                if not video_format.get("container") or not video_format.get(
                    "encoding"
                ):
                    continue

                regular_formats += f"[{len(urls) + 1}. {video_format['resolution']} - {video_format['container']} ({video_format['encoding']})]({video_format['shortened_url']})\n"
                urls.append(video_format)

            video_only = ""
            audio_only = ""

            for video_format in video_info["adaptiveFormats"]:
                if not video_format.get("container") or not video_format.get(
                    "encoding"
                ):
                    continue

                if "resolution" in video_format.keys():
                    video_only += f"[{len(urls) + 1}. {video_format['resolution']} - {video_format['container']} ({video_format['encoding']})]({video_format['shortened_url']})\n"
                else:
                    audio_only += f"[{len(urls) + 1}. {float(video_format['bitrate']) / 1000} kb/s - {video_format['container']} ({video_format['encoding']})]({video_format['shortened_url']})\n"
                urls.append(video_format)

            embed.add_field(name="Regular Formats", value=regular_formats, inline=False)
            embed.add_field(name="Audio Only", value=audio_only, inline=False)
            embed.add_field(name="Video Only", value=video_only, inline=False)

            await ctx.send(embed=embed)

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                choice = await self.bot.wait_for("message", check=check, timeout=60)
            except asyncio.TimeoutError:
                return

            choices = choice.content.split(",")

            if len(choices) > 2:
                await ctx.send("You can only download up to 2 formats at once.")
                return

            try:
                choices = [int(i) - 1 for i in choices]
            except ValueError:
                return

            if ctx.guild:
                limit = ctx.guild.filesize_limit
            else:
                limit = 8000000

            for choice in choices:
                try:
                    video = urls[choice]
                except IndexError:
                    return

                if "clen" in video.keys() and int(video["clen"]) > limit:
                    embed = discord.Embed(
                        title="File too large",
                        description=f"The file you requested is too large to download. Please click [here]({video['url']}) to download it manually.",
                        color=await ctx.embed_color(),
                        url=video["url"],
                    )
                    await ctx.send(embed=embed)
                    return

                embed = discord.Embed(
                    title=f"Downloading option {choice + 1}...",
                    color=await ctx.embed_color(),
                    description="This usually will take a long time. Please be patient.",
                    url=video["url"],
                )
                m = await ctx.send(embed=embed)

                async with self.session.get(
                    video["url"], allow_redirects=True, timeout=1800
                ) as response:
                    if response.status == 200:
                        data = await response.read()

                        if len(data) > limit:
                            embed = discord.Embed(
                                title="File too large",
                                description=f"The file you requested is too large to download. Please click [here]({video['url']}) to download it manually.",
                                color=await ctx.embed_color(),
                                url=video["url"],
                            )
                            try:
                                await m.edit(embed=embed)
                            except discord.NotFound:
                                await ctx.send(embed=embed)
                            return

                        with contextlib.suppress(discord.NotFound):
                            await m.delete()

                        await ctx.send(
                            file=discord.File(
                                io.BytesIO(data),
                                filename=f"file.{video['container']}",
                            )
                        )
                    else:
                        embed = discord.Embed(
                            title="Error",
                            description=f"Something went wrong. Please click [here]({video['url']}) to download it manually.",
                            color=await ctx.embed_color(),
                            url=video["url"],
                        )
                        try:
                            await m.edit(embed=embed)
                        except discord.NotFound:
                            await ctx.send(embed=embed)
