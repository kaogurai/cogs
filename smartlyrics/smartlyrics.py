import asyncio
import re
from typing import Optional, Union

import aiohttp
import discord
import lavalink
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import pagify, text_to_file
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu


class SmartLyrics(commands.Cog):
    """
    Gets lyrics for your current song.
    """

    __version__ = "2.1.2"

    def __init__(self, bot: Red):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.regex = re.compile(
            (
                r"((\[)|(\()).*(of?ficial|feat\.?|"
                r"ft\.?|audio|video|lyrics?|remix|HD).*(?(2)]|\))"
            ),
            flags=re.I,
        )
        # thanks wyn - https://github.com/TheWyn/Wyn-RedV3Cogs/blob/master/lyrics/lyrics.py#L12-13

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx: Context):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def get_lyrics(
        self, *, query: str = None, spotify_id: str = None
    ) -> Optional[dict]:

        if spotify_id:
            params = {
                "spotify_id": spotify_id,
            }
        else:
            params = {
                "query": query,
            }

        headers = {
            "User-Agent": f"Red-DiscordBot, SmartLyrics/v{self.__version__} (https://github.com/kaogurai/cogs)",
        }

        async with self.session.get(
            "https://api.flowery.pw/v1/lyrics", params=params, headers=headers
        ) as resp:
            if resp.status != 200:
                return
            return await resp.json()

    def get_user_status_song(
        self, user: Union[discord.Member, discord.User]
    ) -> Optional[str]:
        s = next(
            (
                s.title
                for s in user.activities
                if s.type == discord.ActivityType.listening
                and isinstance(s, discord.Spotify)
            ),
            None,
        )
        if s:
            return s.track_id

    async def send_results(
        self, ctx: Context, lrc: bool, results: dict, source: Optional[str] = None
    ):
        # Check if there is timed lyrics
        # If there is not, we will ignore the lrc argument
        if not results["lyrics"]["lines"]:
            lrc = False

        if lrc:
            lrc_string = ""
            for line in results["lyrics"]["lines"]:
                start = line["start"]
                # Convert start (ms) to [mm:ss.xx] format
                start = f"{start // 60000:02d}:{start % 60000 // 1000:02d}.{start % 1000 // 10:02d}"
                lrc_string += f"[{start}] {line['text']}\n"

            await ctx.send(
                file=text_to_file(
                    lrc_string,
                    filename=f"{results['track']['artist']} - {results['track']['title']}.lrc",
                )
            )
            return

        embeds = []
        embed_content = [p for p in pagify(results["lyrics"]["text"], page_length=750)]
        for index, page in enumerate(embed_content):
            embed = discord.Embed(
                color=await ctx.embed_color(),
                title=f"{results['track']['title']} by {results['track']['artist']}",
                description=page,
            )
            if results["track"]["media"]["artwork"] is not None:
                embed.set_thumbnail(url=results["track"]["media"]["artwork"])
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
    async def lyrics(
        self, ctx: Context, lrc: Optional[bool] = False, *, query: Optional[str] = None
    ):
        """
        Gets the lyrics for your current song.

        It checks for a query, your voice channel, your spotify status, and your last.fm status (in that order)

        If you would like to download the lyrics as a .lrc file, use `[p]lyrics true` or `[p]lyrics true <query>`
        """
        async with ctx.typing():
            if query:
                results = await self.get_lyrics(query=query)
                if results:
                    await self.send_results(ctx, lrc, results)
                else:
                    await ctx.send(f"No results were found for `{query[:500]}`")
                return

            if ctx.author.voice and ctx.guild.me.voice:
                if ctx.author.voice.channel == ctx.guild.me.voice.channel:
                    try:
                        player = lavalink.get_player(ctx.guild.id)
                    except KeyError:  # no player for that guild
                        player = None
                    if player and player.current:
                        title = player.current.title
                        if "-" not in title:
                            title = player.current.author + " " + title

                        results = await self.get_lyrics(query=title)
                        if results:
                            await self.send_results(ctx, lrc, results, "Voice Channel")
                        else:
                            await ctx.send(f"No results were found for `{title[:500]}`")
                        return

            spotify_id = self.get_user_status_song(ctx.author)
            if spotify_id:
                results = await self.get_lyrics(spotify_id=spotify_id)
                if results:
                    await self.send_results(ctx, lrc, results, "Spotify")
                else:
                    await ctx.send("No results were found for your Spotify status.")
                return

            lastfm_cog = self.bot.get_cog("LastFM")
            lastfm_username = await lastfm_cog.config.user(ctx.author).lastfm_username()

            if lastfm_cog and lastfm_username:
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

                q = f"{trackname} {artistname}"
                results = await self.get_lyrics(query=q)
                if results:
                    await self.send_results(ctx, lrc, results, "Last.fm")
                else:
                    await ctx.send(f"Nothing was found for `{q[:500]}`")
                return

            await ctx.send("Please provide a query to search.")
