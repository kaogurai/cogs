import re

import aiohttp
import discord
import lavalink
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu


class SmartLyrics(commands.Cog):
    """
    Gets lyrics for your current song.
    """

    __version__ = "1.1.2"

    def __init__(self, bot):
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

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def get_lyrics(self, query):
        initial_params = {
            "method": "deezer.getUserData",
            "input": 3,
            "api_version": "1.0",
            "api_token": "",
        }
        async with self.session.get(
            "https://www.deezer.com/ajax/gw-light.php", params=initial_params
        ) as r:
            if r.status != 200:
                return
            json = await r.json()
            api_token = json["results"]["checkForm"]

        search_params = {
            "method": "deezer.pageSearch",
            "input": 3,
            "api_version": "1.0",
            "api_token": api_token,
        }
        search_data = {"query": query, "start": 0, "nb": 5, "top_tracks": True}

        async with self.session.post(
            f"https://www.deezer.com/ajax/gw-light.php?",
            params=search_params,
            json=search_data,
        ) as r:
            if r.status != 200:
                return
            search_results_data = await r.json()

        search_results = search_results_data["results"]["TRACK"]["data"]
        if not search_results:
            return

        track = search_results[0]

        lyrics_params = {
            "method": "song.getLyrics",
            "input": 3,
            "api_version": "1.0",
            "api_token": api_token,
        }
        lyrics_data = {"sng_id": track["SNG_ID"]}
        async with self.session.post(
            f"https://www.deezer.com/ajax/gw-light.php?",
            params=lyrics_params,
            json=lyrics_data,
        ) as r:
            if r.status != 200:
                return
            lyrics_data = await r.json()

        if not lyrics_data["results"]:
            return

        artid = track["ALB_PICTURE"]
        artwork = f"https://e-cdn-images.dzcdn.net/images/cover/{artid}/264x264-000000-80-0-0.jpg"
        return (
            lyrics_data["results"]["LYRICS_TEXT"],
            track["SNG_TITLE"],
            track["ART_NAME"],
            artwork,
        )

    # adapted https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/mod/names.py#L112-L126
    def get_user_status_song(self, user):
        listening_statuses = [
            s for s in user.activities if s.type == discord.ActivityType.listening
        ]
        if not listening_statuses:
            return
        for listening_status in listening_statuses:
            if isinstance(listening_status, discord.Spotify):
                text = ("{artist} {title}").format(
                    artist=discord.utils.escape_markdown(listening_status.artist)
                    if listening_status.artist
                    else "",
                    title=discord.utils.escape_markdown(listening_status.title),
                )
                return text

    async def create_menu(self, ctx, results, source=None):
        embeds = []
        embed_content = [p for p in pagify(results[0], page_length=750)]
        for index, page in enumerate(embed_content):
            embed = discord.Embed(
                color=await ctx.embed_color(),
                title=f"{results[1]} by {results[2]}",
                description=page,
            )
            embed.set_thumbnail(url=results[3])
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
            await menu(ctx, embeds, controls=DEFAULT_CONTROLS, timeout=120)
        else:
            await ctx.send(embed=embeds[0])

    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.command(aliases=["l", "ly"])
    async def lyrics(self, ctx, *, query: str = None):
        """
        Gets the lyrics for your current song.

        If a query (song name) is provided, it will immediately search that.
        Next, it checks if you are in VC and a song is playing.
        Then, it checks if you are listening to a song on spotify.
        Lastly, it checks your last.fm account for your latest song.

        If all of these provide nothing, it will simply ask you to name a song.
        """
        if query:
            if len(query) > 2000:
                return
            results = await self.get_lyrics(query)
            if results:
                await self.create_menu(ctx, results)
                return
            else:
                await ctx.send(f"Nothing was found for `{query}`")
                return

        lastfmcog = self.bot.get_cog("LastFM")

        if ctx.author.voice and ctx.guild.me.voice:
            if ctx.author.voice.channel == ctx.guild.me.voice.channel:
                try:
                    player = lavalink.get_player(ctx.guild.id)
                except KeyError:  # no player for that guild
                    player = None
                if player and player.current:
                    title = player.current.title
                    regex_title = self.regex.sub("", title).strip()
                    renamed_title = regex_title.replace("-", "")
                    results = await self.get_lyrics(renamed_title)
                    if results:
                        await self.create_menu(ctx, results, "Voice Channel")
                        return
                    else:
                        await ctx.send(f"Nothing was found for `{renamed_title}`")
                        return

        statustext = self.get_user_status_song(ctx.author)
        if statustext:
            results = await self.get_lyrics(statustext)
            if results:
                await self.create_menu(ctx, results, "Spotify")
                return
            else:
                await ctx.send(f"Nothing was found for `{statustext}`")
                return

        username = await lastfmcog.config.user(ctx.author).lastfm_username()
        if lastfmcog and username:
            try:
                trackname, artistname, albumname, imageurl  = await lastfmcog.get_current_track(ctx, username)
            except: 
                await ctx.send("Please provide a query to search.")
                return
            
            trackname = f"{trackname} {artistname}"
            results = await self.get_lyrics(trackname)
            if results:
                await self.create_menu(ctx, results, "Last.fm")
                return
            else:
                await ctx.send(f"Nothing was found for `{trackname}`")
                return

        await ctx.send("Please provide a query to search.")
