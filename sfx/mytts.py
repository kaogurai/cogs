from typing import Optional

from redbot.core import commands
from redbot.core.commands import Context

from .abc import MixinMeta


class MyTTSCommand(MixinMeta):
    @commands.group()
    async def mytts(self, ctx: Context):
        """
        Manages your TTS settings.
        """
        pass

    @mytts.command()
    async def voice(self, ctx: Context, voice: Optional[str] = None):
        """
        Changes your TTS voice.
        Type `[p]listvoices` to view all possible voices.
        If no voice is provided, it will show your current voice.
        """

        current_voice = await self.config.user(ctx.author).voice()

        if not voice:
            await ctx.send(f"Your current voice is **{current_voice}**")
            return
        voice = voice.title()
        voice = self.get_voice(voice)
        if voice:
            await self.config.user(ctx.author).voice.set(voice["name"])
            await ctx.send(f"Your new TTS voice is: **{voice['name']}**")
        else:
            await ctx.send(
                f"Sorry, that's not a valid voice. You can view voices with the `{ctx.clean_prefix}listvoices` command."
            )

    @mytts.command()
    async def translate(self, ctx: Context):
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

    @mytts.command()
    async def speed(self, ctx: Context, speed: float = 1.0):
        """
        Changes your TTS speed.

        Speed must be between 0.5 and 10 (both inclusive). The default is 1.0. (0.5 is half speed, 2.0 is double speed, etc.)
        """
        if speed <= 0.5 or speed >= 10:
            await ctx.send("Speed must be between 0.5 and 10.")
            return

        await self.config.user(ctx.author).speed.set(speed)
        await ctx.send(f"Your TTS speed is now {speed}.")
        return
