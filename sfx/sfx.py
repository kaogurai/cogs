from typing import Optional
from urllib.parse import quote

import aiohttp
import discord
import lavalink
from discord.ext import tasks
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Context

try:
    from lavalink import NodeNotFound as NoLavalinkNode
except ImportError:
    NoLavalinkNode = IndexError

from .abc import CompositeMetaClass
from .autotts import AutoTTSMixin
from .channels import TTSChannelMixin
from .commands import BaseCommandsMixin
from .joinandleave import JoinAndLeaveMixin
from .mytts import MyTTSCommand


class SFX(
    AutoTTSMixin,
    TTSChannelMixin,
    BaseCommandsMixin,
    commands.Cog,
    JoinAndLeaveMixin,
    MyTTSCommand,
    metaclass=CompositeMetaClass,
):
    """Plays sound effects, text-to-speech, and sounds when you join or leave a voice channel."""

    __version__ = "6.1.4"

    TTS_API_URL = "https://api.flowery.pw/v1/tts"
    TTS_API_HEADERS = {
        "User-Agent": f"Red-DiscordBot, SFX/{__version__} (https://github.com/kaogurai/cogs)"
    }
    SFX_API_URL = "https://freesound.org/apiv2"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=134621854878007296)
        self.session = aiohttp.ClientSession()
        user_config = {
            "voice": "Christopher",
            "translate": False,
            "join_sound": "",
            "leave_sound": "",
            "speed": 1.0,
        }
        guild_config = {
            "channels": [],
            "allow_join_and_leave": True,
            "allow_autotts": True,
            "join_sound": "",
            "leave_sound": "",
        }
        self.config.register_user(**user_config)
        self.config.register_guild(**guild_config)
        lavalink.register_event_listener(self.ll_check)
        self.bot.loop.create_task(self.set_token())
        self.bot.loop.create_task(self.maybe_get_voices())
        self.bot.loop.create_task(self.get_voices())
        self.last_track_info = {}
        self.current_sfx = {}
        self.repeat_state = {}
        self.voices = []
        self.autotts = []

    def cog_unload(self):
        """
        Runs when the cog is unloaded.

        Closes the Aiohttp session, sets back all the player repeat states, and removes the event listener for lavalink.
        """
        self.bot.loop.create_task(self.session.close())
        self.bot.loop.create_task(self.reset_player_states())
        lavalink.unregister_event_listener(self.ll_check)

    async def red_delete_data_for_user(self, **kwargs):
        """
        Clears a user's data when it's requested.
        """
        await self.config.user_from_id(kwargs["user_id"]).clear()

    def format_help_for_context(self, ctx: Context) -> str:
        """
        Adds the version to the help command.
        """
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    @tasks.loop(hours=48)
    async def get_voices(self) -> None:
        """
        Stores all the available voices in a class attribute.

        We do this so we don't have to make a request every time we want to play a sound.

        It runs every 48 hours since it's uncommon voices will change.
        """
        async with self.session.get(
            f"{self.TTS_API_URL}/voices", headers=self.TTS_API_HEADERS
        ) as req:
            if req.status == 200:
                self.voices = (await req.json())["voices"]

    @tasks.loop(seconds=5)
    async def maybe_get_voices(self) -> None:
        """
        If the TTS API was down for some reason and we can't get the voices, we'll try again every 15 seconds.

        If there's already voices, we can just ignore this since it'll try again in 48 hours.
        """
        if not self.voices:
            await self.get_voices()

    async def reset_player_states(self) -> None:
        """
        Sets all the players to their original repeat state.

        This is called when the cog is unloaded so that the rll repeat states matches the Audio config repeat states.
        """
        for guild_id in self.last_track_info.keys():
            try:
                player = lavalink.get_player(guild_id)
            except NoLavalinkNode:  # Lavalink is probably shutting down
                continue
            player.repeat = self.repeat_state[guild_id]

    async def set_token(self) -> None:
        """
        Sets the token for the SFX API.

        This is called on bot startup and stored in a class attribute so we don't need to call Red's config API every time we want to play a SFX.
        """
        token = await self.bot.get_shared_api_tokens("freesound")
        self.id = token.get("id")
        self.key = token.get("key")

    @commands.Cog.listener()
    async def on_red_api_tokens_update(self, service_name: str, api_tokens: dict):
        """
        Updates the token when the API tokens are updated.

        This is needed to users don't need to reload the cog for it to update.
        """
        if service_name == "freesound":
            self.id = api_tokens.get("id")
            self.key = api_tokens.get("key")

    def generate_url(
        self, voice: str, translate: bool, text: str, speed: float, format: str
    ) -> str:
        """
        Generates the URL for the TTS using kaogurai's TTS API.
        """
        return f"{self.TTS_API_URL}?voice={voice}&translate={translate}&text={quote(text)}&silence=500&audio_format={format}&speed={speed}"

    def get_voice(self, voice: str) -> dict:
        """
        Gets the voice from the voices list.
        """
        for v in self.voices:
            if v["name"] == voice:
                return v

    async def can_tts(self, message: discord.Message):
        ctx = await self.bot.get_context(message)
        command = self.bot.get_command("tts")

        try:
            can = await command.can_run(ctx, change_permission_state=False)
        except commands.CommandError:
            can = False

        return can

    async def play_tts(
        self,
        user: discord.Member,
        voice_channel: discord.VoiceChannel,
        text_channel: discord.TextChannel,
        type: str,
        text: str,
    ) -> None:
        """
        Validates the user's voice still exists and plays the TTS.
        """
        author_data = await self.config.user(user).all()
        author_voice = author_data["voice"]
        author_translate = author_data["translate"]
        author_speed = author_data["speed"]

        is_voice = self.get_voice(author_voice)
        if not is_voice and self.voices:
            await self.config.user(user).voice.clear()
            author_voice = await self.config.user(user).voice()

        url = self.generate_url(
            author_voice, author_translate, text, author_speed, "ogg_opus"
        )

        track_info = ("Text to Speech", user)

        await self.play_sound(
            voice_channel,
            text_channel,
            type,
            url,
            track_info,
        )

    async def play_sound(
        self,
        vc: discord.VoiceChannel,
        channel: Optional[discord.TextChannel],
        type: str,
        url: str,
        track_info: tuple,
    ) -> None:
        """
        Plays an audio file in a voice channel.

        Parameters:
        vc: The voice channel to play the audio in.
        channel: The text channel to send messages in. Can be None.
        type: The type of SFX to play. (joinleave, tts, sfx, autotts, ttschannel)
        url: The URL to play.
        track_info: Tuple of track name and author (discord.py object).
        """
        try:
            player = lavalink.get_player(vc.guild.id)
        except NoLavalinkNode:  # Lavalink hasn't been initialised yet
            if channel and type != "autotts":
                await channel.send(
                    "Either the Audio cog is not loaded or lavalink has not been initialized yet. If this continues to happen, please contact the bot owner."
                )
                return
        except KeyError:
            player = await lavalink.connect(vc)

        repeat_state = player.repeat
        player.repeat = False

        tracks = await player.load_tracks(query=url)
        if not tracks or not tracks.tracks:
            if channel and type != "autotts":
                await channel.send("Something went wrong.")
            return

        track = tracks.tracks[0]
        track_title, track_requester = track_info
        track.title = track_title
        track.requester = track_requester
        track.author = ""
        self.repeat_state[vc.guild.id] = repeat_state

        if type == "sfx":
            await channel.send(f"Playing **{track_title}**...")

        # No queue or anything, just add and play
        if not player.current and not player.queue:
            player.queue.append(track)
            self.current_sfx[vc.guild.id] = track
            await player.play()
            return

        # There's already an SFX or TTS playing, so we can just skip it
        if vc.guild.id in self.current_sfx.keys() and self.current_sfx[vc.guild.id]:
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

    async def ll_check(self, player, event, reason) -> None:
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
