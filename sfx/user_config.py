import discord
from redbot.core import commands
from redbot.core.utils import AsyncIter
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .abc import MixinMeta
from .tts_api import generate_url
from .voices import voices


class UserConfigMixin(MixinMeta):
    def divide_chunks(self, l, n):
        for i in range(0, len(l), n):
            yield l[i : i + n]

    @commands.command(aliases=["voicelist", "voicelists"])
    async def listvoices(self, ctx, give_examples: bool = False):
        """
        Lists all of the TTS voices.

        If you want to see examples of what the voices look like, you can pass True as an argument.
        Keep in mind this will make the command go much slower.
        """
        pages = []
        voices_list = [voice for voice in voices.keys()]
        divided = self.divide_chunks(voices_list, 9)
        async for chunk in AsyncIter(divided):
            embed = discord.Embed(color=await ctx.embed_color())
            async for voice in AsyncIter(chunk):
                if give_examples:
                    url = await generate_url(
                        self,
                        voice,
                        f"Hi, I'm {voice}, nice to meet you.",
                        False,
                    )
                else:
                    url = None
                plugin = voices[voice]["api"](voices, self.session)
                m = ""
                if url:
                    m += f"Example: [Click Here]({url})\n"
                m += f"• Gender: {voices[voice]['gender']}\n"
                m += f"• Language: {voices[voice]['languageName']}\n"
                m += f"• Limit: {plugin.limit}\n"
                m += f"• Source: {plugin.name}"
                if "apiExtra" in voices[voice].keys():
                    m += f" ({voices[voice]['apiExtra']})"

                embed.add_field(name=voice, value=m)
            pages.append(embed)

        for index, embed in enumerate(pages):
            embed.set_footer(
                text=f"Page {index + 1}/{len(pages)} | {len(voices_list)} voices"
            )

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
