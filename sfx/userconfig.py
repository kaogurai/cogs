import discord
from redbot.core import commands
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .abc import MixinMeta
from .voices import voices


class UserConfigMixin(MixinMeta):
    @commands.command(aliases=["voicelist", "voicelists"])
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
