import contextlib
import unicodedata
from abc import ABC
from csv import list_dialects

import aiohttp
import discord
import lavalink
import unidecode
from redbot.core import Config, commands

from .base_commands import BaseCommandsMixin
from .joinandleave import JoinAndLeaveMixin
from .tts_api import generate_url
from .tts_channels import TTSChannelMixin
from .user_config import UserConfigMixin
from .voices import voices


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """Another thing I stole from last.fm for ABC"""


class SFX(
    BaseCommandsMixin,
    commands.Cog,
    JoinAndLeaveMixin,
    UserConfigMixin,
    TTSChannelMixin,
    metaclass=CompositeMetaClass,
):
    """Plays sound effects, text-to-speech, and sounds when you join or leave a voice channel."""

    __version__ = "4.5.3"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=134621854878007296)
        self.session = aiohttp.ClientSession()
        user_config = {
            "voice": "Anna",
            "translate": False,
            "join_sound": "",
            "leave_sound": "",
        }
        guild_config = {"channels": [], "allow_join_and_leave": False}
        self.config.register_user(**user_config)
        self.config.register_guild(**guild_config)
        lavalink.register_event_listener(self.ll_check)
        self.bot.loop.create_task(self.fill_channel_cache())
        self.bot.loop.create_task(self.set_token())
        self.last_track_info = {}
        self.current_sfx = {}
        self.channel_cache = {}
        self.repeat_state = {}

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())
        self.bot.loop.create_task(self.reset_player_states())
        lavalink.unregister_event_listener(self.ll_check)

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    # Keeps all the TTS channels in a dict so we don't need to call config on every message
    async def fill_channel_cache(self):
        all_guilds = await self.config.all_guilds()
        for guild in all_guilds:
            with contextlib.suppress(KeyError):
                self.channel_cache[guild] = all_guilds[guild]["channels"]

    # We modify the player repeat state to avoid issues with SFX, so we need to set it back if the TTS hasn't ended
    async def reset_player_states(self):
        for guild_id in self.last_track_info.keys():
            try:
                player = lavalink.get_player(guild_id)
            except KeyError:
                continue
            player.repeat = self.repeat_state[guild_id]

    # full credits to kable
    # https://github.com/kablekompany/Kable-Kogs/blob/master/decancer/decancer.py#L67
    @staticmethod
    def decancer_text(text):
        text = unicodedata.normalize("NFKC", text)
        text = unicodedata.normalize("NFD", text)
        text = unidecode.unidecode(text)
        text = text.encode("ascii", "ignore")
        text = text.decode("utf-8")
        if text != "":
            return text

    async def set_token(self):
        token = await self.bot.get_shared_api_tokens("freesound")
        self.id = token.get("id")
        self.key = token.get("key")

    @commands.Cog.listener()
    async def on_red_api_tokens_update(self, service_name, api_tokens):
        if service_name == "freesound":
            self.id = api_tokens.get("id")
            self.key = api_tokens.get("key")

    async def play_sound(self, vc, channel, type: str, urls: list, track_info: tuple):
        """
        Plays an audio file in a voice channel.

        Parameters:
        vc: The voice channel to play the audio in.
        channel: The text channel to send messages in. Can be None.
        type: The type of SFX to play. (joinleave, tts, sfx)
        urls: The list of URLs to play. (Only more than one link is supported for TTS)
        track_info: Tuple of track name and author (discord.py object).
        """
        try:
            player = lavalink.get_player(vc.guild.id)
        except KeyError:
            player = await lavalink.connect(vc)

        repeat_state = player.repeat
        player.repeat = False

        tracks = await player.load_tracks(query=urls[0])
        if not tracks.tracks:
            if type == "tts":
                tracks = await player.load_tracks(query=urls[1])
                if not tracks.tracks:
                    if channel:
                        await channel.send("Something went wrong.")
                    return
            else:
                if channel:
                    await channel.send("Something went wrong.")
                return

        track = tracks.tracks[0]
        track_title, track_requester = track_info
        track.title = track_title
        track.requester = track_requester
        track.author = ""
        self.repeat_state[vc.guild.id] = repeat_state

        if type == "sfx":
            await channel.send(f"Playing **{track.title[:100]}**...")

        # No queue or anything, just add and play
        if not player.current and not player.queue:
            player.queue.append(track)
            self.current_sfx[vc.guild.id] = track
            await player.play()
            return

        # There's already an SFX or TTS playing, so we can just skip it
        if (
            vc.guild.id in self.current_sfx.keys()
            and self.current_sfx[vc.guild.id] != None
        ):
            player.queue.insert(0, track)
            await player.skip()
            self.current_sfx[vc.guild.id] = track
            return

        # There's music playing, so we need to store what to set it back to
        # and then move song to second position (1) and skip
        self.last_track_info[vc.guild.id] = (player.current, player.position)
        self.current_sfx[vc.guild.id] = track
        player.queue.insert(0, track)
        player.queue.insert(1, player.current)
        await player.skip()

    async def ll_check(self, player, event, reason):
        guild_current_sfx = self.current_sfx.get(player.guild.id, None)
        guild_last_track_info = self.last_track_info.get(player.guild.id, None)

        # There's nothing to do, so just return
        if not guild_current_sfx and not guild_last_track_info:
            return

        # The track failed to play, so we can just remove it from the current sfx cache
        # We'll also set the repeat state back to what it was before
        if (
            event == lavalink.LavalinkEvents.TRACK_EXCEPTION
            and not guild_current_sfx
            or event == lavalink.LavalinkEvents.TRACK_STUCK
            and not guild_current_sfx
        ):
            if player.guild.id in self.current_sfx:
                del self.current_sfx[player.guild.id]
            if player.guild.id in self.repeat_state:
                player.repeat = self.repeat_state[player.guild.id]
            return

        # The track ended, but nothing was in the queue so we can just remove it from the current sfx cache
        # We'll also set the repeat state back to what it was before
        if event == lavalink.LavalinkEvents.TRACK_END and not player.current:
            if player.guild.id in self.current_sfx:
                del self.current_sfx[player.guild.id]
            if player.guild.id in self.repeat_state:
                player.repeat = self.repeat_state[player.guild.id]
            return

        # The track ended, but there's a queue, so we can just remove it from the current sfx cache
        # Then we'll seek back to where the track was before
        # Lastly we'll also set the repeat state back to what it was before
        if (
            event == lavalink.LavalinkEvents.TRACK_END
            and guild_last_track_info
            and player.current
            and player.current.track_identifier
            == guild_last_track_info[0].track_identifier
        ):
            if player.guild.id in self.current_sfx:
                del self.current_sfx[player.guild.id]
            await player.seek(guild_last_track_info[1] + 2000)
            if player.guild.id in self.last_track_info:
                del self.last_track_info[player.guild.id]
            if player.guild.id in self.repeat_state:
                player.repeat = self.repeat_state[player.guild.id]
