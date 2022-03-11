import io
from typing import Optional

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import escape

from .abc import MixinMeta


class BaseCommandsMixin(MixinMeta):
    @commands.command(usage="<text> [--download]")
    @commands.cooldown(rate=1, per=3, type=discord.ext.commands.cooldowns.BucketType.user)
    @commands.guild_only()
    async def tts(self, ctx, *, text: str):
        """
        Plays the given text as TTS in your current voice channel.

        If you want to download the audio, use the --download flag.
        """
        if "--download" not in text:
            if not ctx.author.voice or not ctx.author.voice.channel:
                await ctx.send("You are not connected to a voice channel.")
                return

            if ctx.guild.me.voice and ctx.guild.me.voice.channel:
                if ctx.author.voice.channel != ctx.guild.me.voice.channel:
                    await ctx.send("You are not in my voice channel.")
                    return
            else:
                current_perms = ctx.author.voice.channel.permissions_for(ctx.guild.me)
                if not current_perms.speak or not current_perms.connect:
                    await ctx.send(
                        "I do not have permissions to connect to and speak in this channel."
                    )
                    return

        author_data = await self.config.user(ctx.author).all()
        author_voice = author_data["voice"]
        author_translate = author_data["translate"]

        is_voice = self.get_voice(author_voice)
        if not is_voice:
            await self.config.user(ctx.author).voice.clear()
            author_voice = await self.config.user(ctx.author).voice()

        url = self.generate_url(
            author_voice, author_translate, text.replace("--download", "")
        )

        if "--download" in text:
            if text == "":
                await ctx.send_help()
                return
            if not ctx.channel.permissions_for(ctx.guild.me).attach_files:
                await ctx.send("I do not have permissions to send files in this channel.")
                return
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    await ctx.send("Something went wrong. Try again later.")
                    return
                data = await resp.read()
                f = io.BytesIO(data)
                f.seek(0)
                await ctx.send(
                    content="Here's your TTS file!",
                    file=discord.File(fp=f, filename="tts.mp3"),
                )
                return

        track_info = ("Text to Speech", ctx.author)
        await self.play_sound(
            ctx.author.voice.channel,
            ctx.channel,
            "tts",
            url,
            track_info,
        )

    async def sfx_check(ctx):
        token = await ctx.bot.get_shared_api_tokens("freesound")
        if token.get("id") and token.get("key"):
            return True
        return False

    @commands.command(usage="<sound> [--download]")
    @commands.cooldown(rate=1, per=3, type=discord.ext.commands.cooldowns.BucketType.user)
    @commands.guild_only()
    @commands.check(sfx_check)
    async def sfx(self, ctx, *, sound: str):
        """
        Plays a sound effect in your current voice channel.

        Sounds are found on https://freesound.org
        """

        if "--download" not in sound:
            if not ctx.author.voice or not ctx.author.voice.channel:
                await ctx.send("You are not connected to a voice channel.")
                return

            if ctx.guild.me.voice and ctx.guild.me.voice.channel:
                if ctx.author.voice.channel != ctx.guild.me.voice.channel:
                    await ctx.send("You are not in my voice channel.")
                    return
            else:
                current_perms = ctx.author.voice.channel.permissions_for(ctx.guild.me)
                if not current_perms.speak or not current_perms.connect:
                    await ctx.send(
                        "I do not have permissions to connect to and speak in this channel."
                    )
                    return

        async with ctx.typing():

            async with self.session.get(
                f"{self.SFX_API_URL}/search/text/",
                params={
                    "query": sound.replace("--download", ""),
                    "token": self.key,
                    "filter": "duration:[0.5 TO 15]",
                },
            ) as resp:
                if resp.status != 200:
                    await ctx.send(
                        "Something went wrong when searching for the sound. Please try again later."
                    )
                    return

                data = await resp.json()
                results = data["results"]

                if not results:
                    await ctx.send("No sounds found for your query.")
                    return

                sound_id = results[0]["id"]

            async with self.session.get(
                f"{self.SFX_API_URL}/sounds/{sound_id}/",
                params={"token": self.key},
            ) as resp:
                if resp.status != 200:
                    await ctx.send(
                        "Something went wrong when getting the sound. Please try again later."
                    )
                    return

                data = await resp.json()
                url = data["previews"]["preview-hq-mp3"]

            name = escape(data["name"].split(f".{data['type']}")[0], formatting=True)[
                :100
            ]
            track_info = (name, ctx.author)

            if "--download" in sound:
                if sound == "":
                    await ctx.send_help()
                    return
                if not ctx.channel.permissions_for(ctx.guild.me).attach_files:
                    await ctx.send(
                        "I do not have permissions to send files in this channel."
                    )
                    return
                async with self.session.get(url) as resp:
                    if resp.status != 200:
                        await ctx.send("Something went wrong. Try again later.")
                        return
                    file_data = await resp.read()
                    f = io.BytesIO(file_data)
                    f.seek(0)
                    await ctx.send(
                        content=f"Here's '{name}'!",
                        file=discord.File(fp=f, filename=f"{name}.mp3"),
                    )
                    return

            await self.play_sound(
                ctx.author.voice.channel,
                ctx.channel,
                "sfx",
                url,
                track_info,
            )
