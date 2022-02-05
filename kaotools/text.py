import urllib

from redbot.core import commands
from zalgo_text import zalgo

from .abc import MixinMeta


class TextMixin(MixinMeta):
    @commands.command()
    async def vowelify(self, ctx: commands.Context, *, text: str):
        """
        Multiplies all vowels in a sentence.
        """
        uwuified = "".join(
            [c if c in "aeiouAEIOU" else (c * 3 if c not in "aeiou" else c) for c in text]
        )
        await ctx.send(uwuified[:1000])

    @commands.command(aliases=["uwuify", "owo", "owoify"])
    async def uwu(self, ctx: commands.Context, *, text: str):
        """
        Uwuifies a sentence.
        """
        encoded = urllib.parse.quote(text)
        async with self.session.get(
            f"https://owo.l7y.workers.dev/?text={encoded}"
        ) as req:
            if req.status == 200:
                data = await req.text()
                await ctx.send(data[:1000])
            else:
                await ctx.send("Sorry, something went wrong.")

    @commands.command(aliases=["zalgoify"])
    async def zalgo(self, ctx: commands.Context, *, text: str):
        """
        Zalgoifies a sentence.
        """
        t = zalgo.zalgo().zalgofy(text)
        await ctx.send(t[:2000])
