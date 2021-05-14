from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
import discord
import aiohttp
import lavalink
import re


class SmartLyrics(commands.Cog):
    """
    Gets lyrics for your current song using the KSoft.SI API.
    """

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

    async def get_lyrics(self, query):
        ksoft_keys = await self.bot.get_shared_api_tokens("ksoftsi")
        key = ksoft_keys.get("api_key")
        url = "https://api.ksoft.si/lyrics/search"
        headers = {"Authorization": "Bearer " + key}
        params = {"q": query, "limit": 1}
        async with self.session.get(url, params=params, headers=headers) as request:
            if request.status == 200:
                results = await request.json()
                try:
                    return [
                        results["data"][0]["lyrics"],
                        results["data"][0]["name"],
                        results["data"][0]["artist"],
                        results["data"][0]["album_art"],
                    ]
                except IndexError:
                    return
        return

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
                        text=f"Powered by KSoft.SI | Source: {source} | Page {index + 1}/{len(embed_content)}"
                    )
                else:
                    embed.set_footer(
                        text=f"Powered by KSoft.SI | Page {index + 1}/{len(embed_content)}"
                    )
            else:
                if source:
                    embed.set_footer(text=f"Powered by KSoft.SI | Source: {source}")
                else:
                    embed.set_footer(text=f"Powered by KSoft.SI")
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
            results = await self.get_lyrics(query)
            if results:
                await self.create_menu(ctx, results)
                return
            else:
                await ctx.send(f"Nothing was found for `{query}`")
                return

        audiocog = self.bot.get_cog("Audio")
        modcog = self.bot.get_cog("Mod")
        lastfmcog = self.bot.get_cog("LastFM")

        async def get_player(ctx):
            try:
                player = lavalink.get_player(ctx.guild.id)
                return player
            except:
                return

        if ctx.author.voice and ctx.guild.me.voice:
            if ctx.author.voice.channel == ctx.guild.me.voice.channel:
                player = await get_player(ctx)
                if audiocog and player and player.current:
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

        if modcog and modcog.handle_listening(ctx.author)[0]:
            statustext = modcog.handle_listening(ctx.author)[0].strip("Listening:")
            removed_spotify = statustext.split("(https://")[0]
            removed_brackets = removed_spotify[2:-1]
            removed_line = removed_brackets.replace("|", "")
            results = await self.get_lyrics(removed_line)
            if results:
                await self.create_menu(ctx, results, "Spotify")
                return
            else:
                await ctx.send(f"Nothing was found for `{removed_line}`")
                return

        if lastfmcog and await lastfmcog.config.user(ctx.author).lastfm_username():
            try:
                data = await lastfmcog.api_request(
                    ctx,
                    {
                        "user": await lastfmcog.config.user(
                            ctx.author
                        ).lastfm_username(),
                        "method": "user.getrecenttracks",
                        "limit": 1,
                    },
                )
            except:
                await ctx.send(
                    "Uh oh, there was an error accessing your Last.FM account."
                )
                return

            tracks = data["recenttracks"]["track"]
            if not tracks:
                await ctx.send("Please provide a query to search.")
                return
            latesttrack = data["recenttracks"]["track"][0]
            trackname = latesttrack["name"] + " " + latesttrack["artist"]["#text"]
            results = await self.get_lyrics(trackname)
            if results:
                await self.create_menu(ctx, results, "Last.fm")
                return
            else:
                await ctx.send(f"Nothing was found for `{trackname}`")
                return

        await ctx.send("Please provide a query to search.")
