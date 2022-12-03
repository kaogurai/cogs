from typing import Any, List, Optional

import discord
from redbot.core import commands
from redbot.core.commands import Context
from redbot.core.utils import AsyncIter
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .abc import MixinMeta


class UserConfigMixin(MixinMeta):
    def divide_chunks(self, list: List[Any], n: int):
        """
        Divides a list into chunks of size n.
        """
        for i in range(0, len(list), n):
            yield list[i : i + n]

    @commands.command(aliases=["voicelist", "voicelists"])
    async def listvoices(self, ctx: Context):
        """
        Lists all of the TTS voices.
        """
        pages = []
        divided = self.divide_chunks(self.voices, 12)
        if not divided:
            await ctx.send(
                "Something is going wrong with the TTS API, please try again later."
            )
            return

        async for chunk in AsyncIter(divided):
            embed = discord.Embed(color=await ctx.embed_color())
            for voice in chunk:
                url = self.generate_url(
                    voice["name"],
                    False,
                    f"Hi, I'm {voice['name']}, nice to meet you.",
                    1.0,
                )
                m = ""
                if url:
                    m += f"Example: [Click Here]({url})\n"
                m += f"• Gender: {voice['gender']}\n"
                m += f"• Language: {voice['language']['name']}\n"
                m += f"• Source: {voice['source']}"

                embed.add_field(name=voice["name"], value=m)
            pages.append(embed)

        for index, embed in enumerate(pages):
            embed.set_footer(
                text=f"Page {index + 1}/{len(pages)} | {len(self.voices)} voices"
            )

        if len(pages) == 1:
            await ctx.send(embed=pages[0])
        else:
            await menu(ctx, pages, DEFAULT_CONTROLS, timeout=60)

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
