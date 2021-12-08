import asyncio
import contextlib
import os
import unicodedata

import aiohttp
import discord
import lavalink
import unidecode
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils.predicates import MessagePredicate

from sfx.api import generate_urls
from sfx.voices import voices


class SFX(commands.Cog):
    """Plays uploaded sounds or text-to-speech."""

    __version__ = "3.0.0"

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

    @commands.command()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def addsfx(self, ctx, name: str, link: str = None):
        """
        Adds a new SFX to this guild.
        Either upload the file as a Discord attachment or use a link.

        Syntax:`[p]addsfx <name>` or `[p]addsfx <name> <link>`.
        """
        guild_sounds = await self.config.guild(ctx.guild).sounds()

        attachments = ctx.message.attachments
        if len(attachments) > 1 or (attachments and link):
            await ctx.send("Please only try to add one SFX at a time.")
            return

        url = ""
        filename = ""
        if attachments:
            attachment = attachments[0]
            url = attachment.url
        elif link:
            url = "".join(link)
        else:
            await ctx.send(
                "You must provide either a Discord attachment or a direct link to a sound."
            )
            return

        filename = "".join(url.split("/")[-1:]).replace("%20", "_")
        file_name, file_extension = os.path.splitext(filename)

        if file_extension not in [".wav", ".mp3"]:
            await ctx.send(
                "Sorry, only SFX in .mp3 and .wav format are supported at this time."
            )
            return

        if name in guild_sounds.keys():
            await ctx.send(
                f"A sound with that filename already exists. Either choose a new name or use {ctx.clean_prefix}delsfx to remove it."
            )
            return

        guild_sounds[name] = url
        await self.config.guild(ctx.guild).sounds.set(guild_sounds)

        await ctx.send("Sound added.")

    @commands.command()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def delsfx(self, ctx, soundname: str):
        """
        Deletes an existing sound.
        """

        guild_sounds = await self.config.guild(ctx.guild).sounds()

        if soundname not in guild_sounds.keys():
            await ctx.send(
                f"That sound does not exist. Try `{ctx.prefix}listsfx` for a list."
            )
            return

        del guild_sounds[soundname]
        await self.config.guild(ctx.guild).sounds.set(guild_sounds)

        await ctx.send(f"Sound deleted.")

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def addglobalsfx(self, ctx, name: str, link: str = None):
        """
        Adds a new SFX to this the bot globally.
        Either upload the file as a Discord attachment or use a link.

        Syntax:`[p]addsfx <name>` or `[p]addsfx <name> <link>`.
        """
        global_sounds = await self.config.sounds()

        attachments = ctx.message.attachments
        if len(attachments) > 1 or (attachments and link):
            await ctx.send("Please only try to add one SFX at a time.")
            return

        url = ""
        if attachments:
            attachment = attachments[0]
            url = attachment.url
        elif link:
            url = "".join(link)
        else:
            await ctx.send(
                "You must provide either a Discord attachment or a direct link to a sound."
            )
            return

        filename = "".join(url.split("/")[-1:]).replace("%20", "_")
        file_name, file_extension = os.path.splitext(filename)

        if file_extension not in [".wav", ".mp3"]:
            await ctx.send(
                "Sorry, only SFX in .mp3 and .wav format are supported at this time."
            )
            return

        if name in global_sounds.keys():
            await ctx.send(
                f"A sound with that filename already exists. Either choose a new name or use {ctx.clean_prefix}delglobalsfx to remove it."
            )
            return

        global_sounds[name] = link
        await self.config.sounds.set(global_sounds)

        await ctx.send("Sound added.")

    @commands.command()
    @checks.is_owner()
    async def delglobalsfx(self, ctx, name: str):
        """
        Deletes an existing global sound.
        """

        global_sounds = await self.config.sounds()

        if name not in global_sounds.keys():
            await ctx.send(
                f"That sound does not exist. Try `{ctx.prefix}listsfx` for a list."
            )
            return

        del global_sounds[name]
        await self.config.sounds.set(global_sounds)

        await ctx.send(f"Sound deleted.")

    @commands.command()
    @commands.guild_only()
    async def listsfx(self, ctx):
        """
        Lists all available sounds for this server.
        """

        guild_sounds = await self.config.guild(ctx.guild).sounds()
        global_sounds = await self.config.sounds()

        if (len(guild_sounds.items()) + len(global_sounds.items())) == 0:
            await ctx.send(f"No sounds found. Use `{ctx.prefix}addsfx` to add one.")
            return

        txt = ""

        if guild_sounds:
            txt += "**Guild Sounds**:\n"
            for sound in guild_sounds:
                txt += sound + "\n"

        if global_sounds:
            txt += "\n**Global Sounds**:\n"
            for sound in global_sounds:
                if guild_sounds and sound in guild_sounds:
                    txt += sound + " (disabled)\n"
                txt += sound + "\n"

        pages = [p for p in pagify(text=txt, delims="\n")]

        for page in pages:
            await ctx.send(page)

    @commands.group()
    async def mytts(self, ctx):
        """
        Manages your TTS settings.
        """
        pass

    @mytts.command()
    async def voice(self, ctx, voice: str = None):
        """
        Changes your TTS voice.
        Type `[p]listvoices` to view all possible voices.
        If no voice is provided, it will show your current voice.
        """

        current_voice = await self.config.user(ctx.author).voice()

        if voice is None:
            await ctx.send(f"Your current voice is **{current_voice}**")
            return
        voice = voice.title()
        if voice in voices.keys():
            await self.config.user(ctx.author).voice.set(voice)
            await ctx.send(f"Your new TTS voice is: **{voice}**")
        else:
            await ctx.send(
                f"Sorry, that's not a valid voice. You can view voices with the `{ctx.clean_prefix}listvoices` command."
            )

    @mytts.command()
    async def speed(self, ctx, speed: int = None):
        """
        Changes your TTS speed.
        If no speed is provided, it will show your current speed.
        The speed range is 0-10 (higher is faster, 5 is normal.)
        """
        current_speed = await self.config.user(ctx.author).speed()

        if speed is None:
            await ctx.send(f"Your current speed is **{current_speed}**")
            return
        if speed < 0:
            await ctx.send("Your speed must be greater than or equal to 0.")
            return
        if speed > 10:
            await ctx.send("Your speed must be less than or equal to 10.")
            return

        await self.config.user(ctx.author).speed.set(speed)
        await ctx.send(f"Your new speed is **{speed}**. ")

    @mytts.command()
    async def volume(self, ctx, volume: int = None):
        """
        Changes your TTS volume.
        If no volume is provided, it will show your current volume.
        The volume range is 0-10 (higher is higher, 10 is normal.)
        """
        current_volume = await self.config.user(ctx.author).volume()

        if volume is None:
            await ctx.send(f"Your volume speed is **{current_volume}**")
            return
        if volume < 0:
            await ctx.send("Your volume must be greater than or equal to 0.")
            return
        if volume > 10:
            await ctx.send("Your volume must be less than or equal to 10.")
            return

        await self.config.user(ctx.author).volume.set(volume)
        await ctx.send(f"Your new volume is **{volume}**. ")

    @mytts.command()
    async def translate(self, ctx):
        """
        Toggles your TTS translation.
        """
        current_translate = await self.config.user(ctx.author).translate()

        if current_translate:
            await self.config.user(ctx.author).translate.set(False)
            await ctx.send("Your TTS translation is now off.")
        else:
            await self.config.user(ctx.author).translate.set(True)
            await ctx.send("Your TTS translation is now on.")

    @commands.command()
    async def listvoices(self, ctx):
        """
        Lists all the TTS voices in the selected language.

        If no language is provided, it will list sthe voices in English.
        Use 'all' as the language code to view all voices.
        """
        current_voice = await self.config.user(ctx.author).voice()
        pages = []
        for voice in voices:
            embed = discord.Embed(color=await ctx.embed_color(), title=voice)
            embed.description = (
                "```yaml\n"
                f"Gender: {voices[voice]['gender']}\n"
                f"Language: {voices[voice]['languageName']}\n"
                "```"
            )
            if current_voice == voice:
                embed.description = (
                    "```yaml\n"
                    f"Active: True\n"
                    f"Gender: {voices[voice]['gender']}\n"
                    f"Language: {voices[voice]['languageName']}\n"
                    "```"
                )
            pages.append(embed)

        for index, embed in enumerate(pages):
            if len(pages) > 1:
                embed.set_footer(text=f"Voice {index + 1}/{len(pages)}")

        if len(pages) == 1:
            await ctx.send(embed=pages[0])
        else:
            await menu(ctx, pages, DEFAULT_CONTROLS, timeout=60)

    @commands.group()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def ttschannel(self, ctx):
        """
        Configures automatic TTS channels.
        """
        pass

    @ttschannel.command()
    async def add(self, ctx, channel: discord.TextChannel):
        """
        Adds a channel for automatic TTS.
        """
        channel_list = await self.config.guild(ctx.guild).channels()
        if channel.id not in channel_list:
            channel_list.append(channel.id)
            await self.config.guild(ctx.guild).channels.set(channel_list)
            self.channel_cache[ctx.guild.id] = channel_list

            await ctx.send(
                f"Okay, {channel.mention} will now be used as a TTS channel."
            )
        else:
            await ctx.send(
                f"{channel.mention} is already a TTS channel, did you mean use the `{ctx.clean_prefix}ttschannel remove` command?"
            )

    @ttschannel.command(aliases=["delete", "del"])
    async def remove(self, ctx, channel: discord.TextChannel):
        """
        Removes a channel for automatic TTS.
        """
        channel_list = await self.config.guild(ctx.guild).channels()
        if channel.id in channel_list:
            channel_list.remove(channel.id)
            await self.config.guild(ctx.guild).channels.set(channel_list)
            self.channel_cache[ctx.guild.id] = channel_list
            await ctx.send(f"Okay, {channel.mention} is no longer a TTS channel.")
        else:
            await ctx.send(
                f"{channel.mention} isn't a TTS channel, did you mean use the `{ctx.clean_prefix}ttschannel add` command?"
            )

    @ttschannel.command()
    async def clear(self, ctx):
        """
        Removes all the channels for automatic TTS.
        """
        channel_list = await self.config.guild(ctx.guild).channels()
        if not channel_list:
            await ctx.send("There's no channels in the config.")
        else:
            try:
                await ctx.send(
                    "Are you sure you want to clear all this server's TTS channels? Respond with yes or no."
                )
                predictate = MessagePredicate.yes_or_no(ctx, user=ctx.author)
                await ctx.bot.wait_for("message", check=predictate, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send(
                    "You never responded, please use the command again to clear all of this server's TTS channels."
                )
                return
            if predictate.result:
                await self.config.guild(ctx.guild).channels.clear()
                del self.channel_cache[ctx.guild.id]
                await ctx.send("Okay, I've cleared all TTS channels for this server.")
            else:
                await ctx.send("Okay, I won't clear any TTS channels.")

    @ttschannel.command()
    async def list(self, ctx):
        """
        Shows all the channels for automatic TTS.
        """
        try:
            channel_list = self.channel_cache[ctx.guild.id]
        except KeyError:
            channel_list = None
        if not channel_list:
            await ctx.send("This server doesn't have any TTS channels set up.")
        else:
            text = "".join(
                "<#" + str(channel) + "> - " + str(channel) + "\n"
                for channel in channel_list
            )
            pages = [p for p in pagify(text=text, delims="\n")]
            embeds = []
            for index, page in enumerate(pages):
                embed = discord.Embed(
                    title="Automatic TTS Channels",
                    color=await ctx.embed_colour(),
                    description=page,
                )
                if len(embeds) > 1:
                    embed.set_footer(text=f"Page {index+1}/{len(pages)}")
                embeds.append(embed)

            if len(pages) == 1:
                await ctx.send(embed=embeds[0])
            else:
                await menu(ctx, embeds, DEFAULT_CONTROLS, timeout=60)

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return
        if not message.channel.permissions_for(message.guild.me).send_messages:
            return
        if await self.bot.allowed_by_whitelist_blacklist(who=message.author) is False:
            return
        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return
        try:
            channel_list = self.channel_cache[message.guild.id]
        except KeyError:
            return

        if not channel_list:
            return
        if message.channel.id not in channel_list:
            return

        if not message.author.voice or not message.author.voice.channel:
            await message.channel.send("You are not connected to a voice channel.")
            return

        author_data = await self.config.user(message.author).all()
        author_voice = author_data["voice"]
        author_speed = author_data["speed"]
        author_volume = author_data["volume"]
        author_translate = author_data["translate"]

        if author_voice not in voices.keys():
            await self.config.user(message.author).voice.clear()
            author_voice = "Anna"

        text = self.decancer_text(message.clean_content)

        if text is None:
            await message.channel.send("That's not a valid message, sorry.")
            return

        char_number = len(text)

        if char_number > 1000:
            await message.channel.send(
                f"Sorry, I limit TTS to 1000 characters to avoid abuse. ({char_number}/1000)"
            )
            return

        urls = await generate_urls(
            self, author_voice, text, author_speed, author_volume, author_translate
        )

        await self.play_sfx(
            message.author.voice.channel,
            message.channel,
            True,
            author_data,
            text,
            urls,
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
