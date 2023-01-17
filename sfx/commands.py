import argparse
import asyncio
import io
from typing import Any, List

import discord
from redbot.core import commands
from redbot.core.commands import BadArgument, Context, Converter
from redbot.core.utils.chat_formatting import escape
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from thefuzz import process

from .abc import MixinMeta


class NoExitParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise BadArgument()


class TTSConverter(Converter):
    def divide_chunks(self, list: List[Any], n: int):
        """
        Divides a list into chunks of size n.
        """
        for i in range(0, len(list), n):
            yield list[i : i + n]

    async def convert(self, ctx: Context, argument: str) -> int:
        argument = argument.replace("—", "--")  # For iOS's weird smart punctuation

        user_config = await ctx.cog.config.user(ctx.author).all()

        parser = NoExitParser(add_help=False)
        parser.add_argument("text", type=str, nargs="*")
        parser.add_argument("--voices", action="store_true")
        parser.add_argument(
            "--voice", type=str, default=user_config["voice"], nargs="*"
        )
        parser.add_argument("--speed", type=float, default=user_config["speed"])
        parser.add_argument(
            "--translate", action="store_true", default=False
        )
        parser.add_argument("--no-translate", action="store_true", default=False)
        parser.add_argument("--download", action="store_true")

        try:
            values = vars(parser.parse_args(argument.split(" ")))
        except Exception:
            raise BadArgument()

        translate = user_config["translate"]
        if values["translate"]:
            translate = True
        elif values["no_translate"]:
            translate = False

        values["translate"] = translate

        if not values["text"] and not values["voices"]:
            raise BadArgument()

        values["text"] = " ".join(values["text"])

        voices_list = [voice["name"] for voice in ctx.cog.voices]

        if user_config["voice"] not in voices_list:
            await ctx.cog.config.user(ctx.author).voice.clear()

        if values["voice"] not in voices_list:
            values["voice"] = process.extract(
                " ".join(values["voice"]),
                voices_list,
                limit=1,
            )[0][0]

        if values["voices"]:
            pages = []
            divided = self.divide_chunks(ctx.cog.voices, 12)
            if not divided:
                await ctx.send(
                    "Something is going wrong with the TTS API, please try again later."
                )
                return

            for chunk in divided:
                embed = discord.Embed(color=await ctx.embed_color())
                for voice in chunk:
                    url = ctx.cog.generate_url(
                        voice["name"],
                        False,
                        f"Hi, I'm {voice['name']}, nice to meet you.",
                        1.0,
                        "mp3",
                    )
                    m = f"""
                    Example: [Click Here]({url})
                    • Gender: {voice['gender']}
                    • Language: {voice['language']['name']}
                    • Source: {voice['source']}
                    """
                    embed.add_field(name=voice["name"], value=m)
                pages.append(embed)

            for index, embed in enumerate(pages):
                embed.set_footer(
                    text=f"Page {index + 1}/{len(pages)} | {len(ctx.cog.voices)} voices"
                )

            asyncio.create_task(menu(ctx, pages, DEFAULT_CONTROLS))
            return

        return values


class BaseCommandsMixin(MixinMeta):
    @commands.command()
    @commands.cooldown(
        rate=1, per=3, type=discord.ext.commands.cooldowns.BucketType.user
    )
    @commands.guild_only()
    async def tts(self, ctx: Context, *, args: TTSConverter):
        """
        Plays the given text as TTS in your current voice channel.

        Arguments:
            text: The text to be spoken.
            `--voice`: The voice to use.
            `--speed`: The speed to speak at.
            `--download`: Whether to download the file instead of playing it.
            `--translate`: Whether to translate the text to the voice language. Use `--no-translate` if your default is `True`.

            `--voices`: Lists all available voices. Cannot be used with other arguments.
        """
        if not args:
            return

        if not args["download"]:
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

            if not ctx.author.voice.channel.permissions_for(ctx.author).speak:
                await ctx.channel.send(
                    "You don't have permission to speak in this channel."
                )
                return

        url = self.generate_url(
            args["voice"],
            args["translate"],
            args["text"],
            args["speed"],
            "mp3" if args["download"] else "ogg_opus",
        )

        if args["download"]:
            if not ctx.channel.permissions_for(ctx.guild.me).attach_files:
                await ctx.send(
                    "I do not have permissions to send files in this channel."
                )
                return

            async with self.session.get(url, headers=self.TTS_API_HEADERS) as resp:
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
    @commands.cooldown(
        rate=1, per=3, type=discord.ext.commands.cooldowns.BucketType.user
    )
    @commands.guild_only()
    @commands.check(sfx_check)
    async def sfx(self, ctx: Context, *, sound: str):
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

            if not ctx.author.voice.channel.permissions_for(ctx.author).speak:
                await ctx.channel.send(
                    "You don't have permission to speak in this channel."
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
