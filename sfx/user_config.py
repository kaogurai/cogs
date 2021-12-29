import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_list
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .abc import MixinMeta
from .tts_api import generate_url
from .voices import voices


class UserConfigMixin(MixinMeta):
    def divide_chunks(self, l, n):
        for i in range(0, len(l), n):
            yield l[i : i + n]

    @commands.command(aliases=["voicelist", "voicelists"])
    async def listvoices(self, ctx):
        """
        Lists all of the TTS voices.
        """
        pages = []
        voices_list = [voice for voice in voices.keys()]
        divided = self.divide_chunks(voices_list, 9)
        for chunk in divided:
            embed = discord.Embed(color=await ctx.embed_color())
            for voice in chunk:
                url = await generate_url(
                    self,
                    voice,
                    f"Hi, I'm {voice}, nice to meet you.",
                    False,
                )
                m = (
                    f"Example: [Click Here]({url})\n"
                    f"• Gender: {voices[voice]['gender']}\n"
                    f"• Language: {voices[voice]['languageName']}\n"
                )
                embed.add_field(name=voice, value=m)
            pages.append(embed)

        for index, embed in enumerate(pages):
            if len(pages) > 1:
                embed.set_footer(text=f"Page {index + 1}/{len(pages)}")

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
