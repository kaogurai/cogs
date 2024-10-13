import asyncio
import re
from typing import Optional, Union

import aiohttp
import discord
import lavalink
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu


class SmartLyrics(commands.Cog):
    """
    Gets lyrics for your current song.
    """

    __version__ = "3.0.5"

    def __init__(self, bot: Red):
        """
        Initalizes the cog by setting up the HTTP session with the
        correct headers and setting the RegEx.
        """
        self.bot = bot
        self.session = aiohttp.ClientSession(
            headers={
                "X-Genius-iOS-Version": "7.1.0",
                "X-Genius-Logged-Out": "true",
                "User-Agent": "Genius/1160 CFNetwork/1568.100.1.2.1 Darwin/24.0.0",
            }
        )
        # thanks wyn for the RegEx
        # https://github.com/TheWyn/Wyn-RedV3Cogs/blob/master/lyrics/lyrics.py#L12-13
        self.regex = re.compile(
            (
                r"((\[)|(\()).*(of?ficial|feat\.?|"
                r"ft\.?|audio|video|lyrics?|remix|HD).*(?(2)]|\))"
            ),
            flags=re.I,
        )

    def cog_unload(self) -> None:
        """
        Closes the HTTP session when the cog is unloaded.
        """
        self.bot.loop.create_task(self.session.close())

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

    async def _search(self, query: str) -> Optional[int]:
        """
        Uses the Genius API to search for track IDs.
        """
        filtered = self.regex.sub("", query).strip()
        params = {
            "q": filtered,
        }

        async with self.session.get(
            "https://api.genius.com/search/multi", params=params
        ) as r:
            if r.status != 200:
                return

            j = await r.json()

            tracks = j["response"]["sections"][1]["hits"]
            if not tracks:
                return

            return tracks[0]["result"]["id"]

    async def _get_lyrics(self, query: str) -> Optional[dict]:
        """
        Uses the Genius API to get lyrics.
        """
        track_id = await self._search(query)
        if not track_id:
            return

        params = {
            "text_format": "plain,dom",
        }
        async with self.session.get(
            "https://api.genius.com/songs/" + str(track_id),
            params=params,
        ) as r:
            if r.status != 200:
                return

            j = await r.json()

            return {
                "title": j["response"]["song"]["full_title"],
                "artwork": j["response"]["song"]["song_art_image_url"],
                "lyrics": j["response"]["song"]["lyrics"]["plain"],
            }

    def _get_user_status_song(
        self, user: Union[discord.Member, discord.User]
    ) -> Optional[str]:
        """
        Possibly returns a string of the user's spotify status.
        """
        return next(
            (
                s.title + " " + s.artist
                for s in user.activities
                if s.type == discord.ActivityType.listening
                and isinstance(s, discord.Spotify)
            ),
            None,
        )

    async def _send_results(
        self, ctx: Context, data: dict, source: Optional[str] = None
    ):
        """
        Package the results into embeds and sends them to the user.
        """
        embeds = []
        embed_content = [p for p in pagify(data["lyrics"], page_length=750)]
        for index, page in enumerate(embed_content):
            embed = discord.Embed(
                color=await ctx.embed_color(),
                title=data["title"],
                description=page,
            )
            if data["artwork"] is not None:
                embed.set_thumbnail(url=data["artwork"])
            if len(embed_content) != 1:
                if source:
                    embed.set_footer(
                        text=f"Source: {source} | Page {index + 1}/{len(embed_content)}"
                    )
                else:
                    embed.set_footer(text=f"Page {index + 1}/{len(embed_content)}")
            else:
                if source:
                    embed.set_footer(text=f"Source: {source}")
            embeds.append(embed)

        if len(embed_content) != 1:
            asyncio.create_task(
                menu(ctx, embeds, controls=DEFAULT_CONTROLS, timeout=120)
            )
        else:
            await ctx.send(embed=embeds[0])

    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.command(aliases=["l", "ly"])
    async def lyrics(self, ctx: Context, *, query: Optional[str] = None):
        """
        Gets the lyrics for your current song.

        It checks for a query, your voice channel, your spotify status, and your last.fm status (in that order)
        """
        async with ctx.typing():
            if query:
                results = await self._get_lyrics(query)
                if results:
                    await self._send_results(ctx, results, "Query")
                else:
                    await ctx.send(f"No results were found for `{query[:500]}`")
                return

            if ctx.author.voice and ctx.guild.me.voice and ctx.author.voice.channel == ctx.guild.me.voice.channel:
                try:
                    player = ctx.pylav.get_player(ctx.guild.id)
                    title = await player.current.title()
                    if "-" not in title:
                        title = (await player.current.author()) + " " + title
                except AttributeError:
                    try:
                        player = lavalink.get_player(ctx.guild.id)
                    except KeyError:  # no player for that guild
                        player = None
                    if player and player.current:
                        title = player.current.title
                        if "-" not in title:
                            title = player.current.author + " " + title
                    else:
                        title = None
                if title:
                    results = await self._get_lyrics(title)
                    if results:
                        await self._send_results(ctx, results, "Voice Channel")
                        return

            spotify_track = self._get_user_status_song(ctx.author)
            if spotify_track:
                results = await self._get_lyrics(spotify_track)
                if results:
                    await self._send_results(ctx, results, "Spotify")
                    return

            lastfm_cog = self.bot.get_cog("LastFM")

            if lastfm_cog:
                lastfm_username = await lastfm_cog.config.user(
                    ctx.author
                ).lastfm_username()
                if lastfm_username:
                    try:
                        (
                            trackname,
                            artistname,
                            albumname,
                            imageurl,
                        ) = await lastfm_cog.get_current_track(ctx, lastfm_username)
                    except:
                        await ctx.send("Please provide a query to search.")
                        return

                    results = await self._get_lyrics(f"{trackname} {artistname}")
                    if results:
                        await self._send_results(ctx, results, "Last.fm")
                        return

            await ctx.send("Please provide a query to search.")
