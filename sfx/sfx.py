import contextlib
import unicodedata
from abc import ABC

import aiohttp
import discord
import lavalink
import unidecode
from redbot.core import Config, commands

from sfx.api import generate_urls
from sfx.voices import voices

from .channelconfig import ChannelConfigMixin
from .sfxconfig import SFXConfigMixin
from .userconfig import UserConfigMixin


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """Another thing I stole from last.fm for ABC"""


class SFX(
    ChannelConfigMixin,
    commands.Cog,
    SFXConfigMixin,
    UserConfigMixin,
    metaclass=CompositeMetaClass,
):
    """Plays uploaded sounds or text-to-speech."""

    __version__ = "3.2.0"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=134621854878007296)
        self.session = aiohttp.ClientSession()
        user_config = {
            "voice": "Anna",
            "speed": 5,
            "pitch": 5,
            "volume": 5,
            "translate": False,
        }
        guild_config = {"sounds": {}, "channels": []}
        global_config = {"sounds": {}, "schema_version": 0}
        self.config.register_user(**user_config)
        self.config.register_guild(**guild_config)
        self.config.register_global(**global_config)
        lavalink.register_event_listener(self.ll_check)
        self.bot.loop.create_task(self.check_config_version())
        self.bot.loop.create_task(self.fill_channel_cache())
        self.last_track_info = {}
        self.current_sfx = {}
        self.channel_cache = {}

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())
        lavalink.unregister_event_listener(self.ll_check)

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def check_config_version(self):
        schema_version = await self.config.schema_version()
        if schema_version == 0:
            await self.config.clear_all_users()
            await self.config.sounds.clear()
            all_guilds = await self.config.all_guilds()
            for guild in all_guilds:
                await self.config.guild_from_id(guild).sounds.clear()
            await self.config.schema_version.set(1)

    async def fill_channel_cache(self):
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            with contextlib.suppress(KeyError):
                self.channel_cache[guild] = all_guilds[guild]["channels"]

    # full credits to kable
    # https://github.com/kablekompany/Kable-Kogs/blob/master/decancer/decancer.py#L67
    @staticmethod
    def decancer_text(text):
        text = unicodedata.normalize("NFKC", text)
        text = unicodedata.normalize("NFD", text)
        text = unidecode.unidecode(text)
        text = text.encode("ascii", "ignore")
        text = text.decode("utf-8")
        if text == "":
            return
        return text

    @commands.command()
    @commands.cooldown(
        rate=1, per=3, type=discord.ext.commands.cooldowns.BucketType.user
    )
    @commands.guild_only()
    async def tts(self, ctx, *, text):
        """
        Plays the given text as TTS in your current voice channel.
        """

        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("You are not connected to a voice channel.")
            return

        author_data = await self.config.user(ctx.author).all()
        author_voice = author_data["voice"]
        author_speed = author_data["speed"]
        author_volume = author_data["volume"]
        author_translate = author_data["translate"]

        if author_voice not in voices.keys():
            await self.config.user(ctx.author).voice.clear()
            author_voice = "Anna"

        text = self.decancer_text(text)

        if text is None:
            await ctx.send("That's not a valid message, sorry.")
            return

        urls = await generate_urls(
            self, author_voice, text, author_speed, author_volume, author_translate
        )
        await self.play_sfx(
            ctx.author.voice.channel, ctx.channel, True, author_data, text, urls
        )

    @commands.command()
    @commands.cooldown(
        rate=1, per=3, type=discord.ext.commands.cooldowns.BucketType.user
    )
    @commands.guild_only()
    async def sfx(self, ctx, sound: str):
        """
        Plays an existing sound in your current voice channel.
        If a guild SFX exists with the same name as a global one, the guild SFX will be played.
        """

        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("You are not connected to a voice channel.")
            return

        guild_sounds = await self.config.guild(ctx.guild).sounds()
        global_sounds = await self.config.sounds()

        if sound not in guild_sounds.keys() and sound not in global_sounds.keys():
            await ctx.send(
                f"That sound does not exist. Try `{ctx.clean_prefix}listsfx` for a list."
            )
            return

        if sound in guild_sounds.keys():
            link = guild_sounds[sound]
        else:
            link = global_sounds[sound]

        await self.play_sfx(
            ctx.author.voice.channel, ctx.channel, False, None, None, [link]
        )

    async def play_sfx(self, vc, channel, is_tts, author_data, text, link):
        try:
            player = lavalink.get_player(vc.guild.id)
        except KeyError:
            player = None
        if not player:
            try:
                player = await lavalink.connect(vc)
            except IndexError:
                return
        link = link[
            0
        ]  # could be rewritten to add ALL links, the tts backend is ready for it
        tracks = await player.load_tracks(query=link)
        if not tracks.tracks:
            await channel.send("Something went wrong.")
            return

        track = tracks.tracks[0]

        if player.current is None and not player.queue:
            player.queue.append(track)
            self.current_sfx[vc.guild.id] = track
            await player.play()
            return

        try:
            csfx = self.current_sfx[vc.guild.id]
        except KeyError:
            csfx = None

        if csfx is not None:
            player.queue.insert(0, track)
            await player.skip()
            self.current_sfx[vc.guild.id] = track
            return

        self.last_track_info[vc.guild.id] = (player.current, player.position)
        self.current_sfx[vc.guild.id] = track
        player.queue.insert(0, track)
        player.queue.insert(1, player.current)
        await player.skip()

    async def ll_check(self, player, event, reason):
        try:
            csfx = self.current_sfx[player.guild.id]
        except KeyError:
            csfx = None

        try:
            lti = self.last_track_info[player.guild.id]
        except KeyError:
            lti = None

        if csfx is None and lti is None:
            return

        if (
            event == lavalink.LavalinkEvents.TRACK_EXCEPTION
            and csfx is not None
            or event == lavalink.LavalinkEvents.TRACK_STUCK
            and csfx is not None
        ):
            if player.guild.id in self.current_sfx:
                del self.current_sfx[player.guild.id]
            return

        if (
            event == lavalink.LavalinkEvents.TRACK_END
            and player.current is None
            and csfx is not None
        ):
            if player.guild.id in self.current_sfx:
                del self.current_sfx[player.guild.id]
            return

        if (
            event == lavalink.LavalinkEvents.TRACK_END
            and lti is not None
            and player.current
            and player.current.track_identifier == lti[0].track_identifier
        ):
            if player.guild.id in self.current_sfx:
                del self.current_sfx[player.guild.id]
            await player.seek(lti[1])
            if player.guild.id in self.last_track_info:
                del self.last_track_info[player.guild.id]
