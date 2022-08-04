from copy import copy
from typing import Optional

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu


class Radio(commands.Cog):
    """
    Saves radio stations for easy access.
    """

    __version__ = "1.0.3"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=69420)
        self.config.register_global(stations={})

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx: Context):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    def play_station(self, ctx: Context, name: str):
        """
        Plays a radio station.
        """
        msg = copy(ctx.message)
        msg.content = f"{ctx.prefix}bumpplay true {name}"
        self.bot.dispatch("message", msg)

    @commands.command()
    async def radio(self, ctx: Context, station: Optional[str] = None):
        """
        Play a radio station.

        If you already know the station name, run the command with the station name.
        Otherwise, the stations will appear and you will be asked for a name.

        Examples:
        - `[p]radio` - Shows a list of stations and asks for one to play.
        - `[p]radio pop` - Plays the station 'pop'
        - `[p]radio country` - Plays the station 'country'
        """
        stations = await self.config.stations()
        if not stations:
            await ctx.send("There are no stations saved.")
            return

        names = [name for name in stations]
        if station:
            station = station.lower()
            if station not in names:
                await ctx.send("That station doesn't exist.")
                return
            self.play_station(ctx, stations[station])
            return
        humanized_names = humanize_list(names)
        pages = [p for p in pagify(humanized_names, page_length=750, delims=[","])]
        embeds = []
        for i, page in enumerate(pages):
            embed = discord.Embed(
                title="Reply with the station name you'd like to play.",
                description=page,
                color=await ctx.embed_color(),
            )
            if len(pages) > 1:
                embed.set_footer(text=f"Page {i + 1}/{len(pages)}")
            embeds.append(embed)
        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            await menu(ctx, embeds, DEFAULT_CONTROLS)

        await ctx.send("Which station would you like to play?")
        response = await self.bot.wait_for(
            "message", check=lambda m: m.author == ctx.author
        )
        station = response.content.split()[0]
        station = station.lower()
        if station not in names:
            await ctx.send("That station doesn't exist.")
            return
        self.play_station(ctx, stations[station])

    @commands.group()
    @commands.is_owner()
    async def radioset(self, ctx: Context):
        """
        Commands to add/remove radio stations.
        """

    @radioset.command()
    async def add(self, ctx: Context, name: str, url: str):
        """
        Add a radio station.

        Examples:
        - `[p]radioset pop http://hfm.amgradio.ru/HypeFM`
        - `[p]radioset country http://ais-edge23-dal02.cdnstream.com/1976_64.aac`
        """
        stations = await self.config.stations()
        name = name.lower()
        if name in stations:
            await ctx.send("That station already exists.")
            return
        stations[name] = url
        await self.config.stations.set(stations)
        await ctx.send("Station added.")

    @radioset.command()
    async def remove(self, ctx: Context, name: str):
        """
        Remove a radio station.

        Examples:
        - `[p]radioset remove pop`
        """
        stations = await self.config.stations()
        name = name.lower()
        if name not in stations:
            await ctx.send("That station doesn't exist.")
            return
        del stations[name]
        await self.config.stations.set(stations)
        await ctx.send("Station removed.")
