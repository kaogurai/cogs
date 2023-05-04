import asyncio
from io import BytesIO
from typing import Optional

import colorgram
import discord
from PIL import Image, ImageDraw
from redbot.core import commands
from redbot.core.commands import Context

from .abc import MixinMeta


class ImageMixin(MixinMeta):
    @commands.command()
    @commands.bot_has_permissions(attach_files=True)
    async def obama(self, ctx: Context, *, text: str):
        """
        Generate a video of Obama saying something.

        There is a limit of 280 characters.
        """
        if len(text) > 280:
            await ctx.send("Your message needs to be 280 characters or less.")
            return
        async with ctx.typing():
            async with self.session.post(
                "http://talkobamato.me/synthesize.py",
                data={"input_text": text},
            ) as resp:
                if resp.status != 200:
                    await ctx.send("Something went wrong when trying to get the video.")
                    return
                key = resp.url.query["speech_key"]

            async with self.session.get(
                f"http://talkobamato.me/synth/output/{key}/obama.mp4"
            ) as resp:
                if resp.status != 200:
                    await ctx.send("Something went wrong when trying to get the video.")
                    return
                res = await resp.read()
                if len(res) < 100:  # File incomplete
                    await asyncio.sleep(3)  # Needs some more time to generate, I guess
                    async with self.session.get(
                        f"http://talkobamato.me/synth/output/{key}/obama.mp4"
                    ) as resp:
                        if resp.status != 200:
                            await ctx.send(
                                "Something went wrong when trying to get the video."
                            )
                            return
                        res = await resp.read()
            bfile = BytesIO(res)
            bfile.seek(0)
            await ctx.send(file=discord.File(bfile, filename="obama.mp4"))

    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["ship", "lovecalc"])
    async def lovecalculator(
        self, ctx: Context, user: discord.User, user2: Optional[discord.User] = None
    ):
        """
        Calculates the amount of love between two users.
        """
        if user2 is None:
            user2 = ctx.author
        love = (user.id + user2.id) % 100
        ua = user.display_avatar.with_format("png").url
        u2a = user2.display_avatar.with_format("png").url
        u = f"https://api.martinebot.com/v1/imagesgen/ship?percent={love}&first_user={ua}&second_user={u2a}&no_69_percent_emoji=false"
        t = f"{user.name} and {user2.name} have {love}% compatibility."
        e = discord.Embed(color=await ctx.embed_color(), title=t)
        e.set_image(url=u)
        e.set_footer(text="Powered by api.martinebot.com")
        await ctx.send(embed=e)

    def get_color_palette(self, img: BytesIO) -> discord.File:
        colors = colorgram.extract(img, 10)
        if sorted:
            colors.sort(key=lambda c: c.rgb)
        dimensions = (100 * len(colors), 100)
        final = Image.new("RGBA", dimensions)
        a = ImageDraw.Draw(final)
        start = 0
        for color in colors:
            a.rectangle([(start, 0), (start + 100, 100)], fill=color.rgb)
            start = start + 100
        final = final.resize((100 * len(colors), 100), resample=Image.ANTIALIAS)
        file = BytesIO()
        final.save(file, "png")
        file.name = f"palette.png"
        file.seek(0)
        image = discord.File(file)
        return image

    @commands.command(aliases=["pfppalette", "pfpalette"])
    @commands.bot_has_permissions(attach_files=True)
    async def palette(self, ctx: Context, link: Optional[str] = None, sorted=False):
        """
        Get the color palette of an image.

        By default it is sorted by prominence, but you can sort it by rgb by passing true.

        Thanks flare for making this!
        """
        if not link:
            if not ctx.message.attachments:
                link = str(ctx.author.avatar_url_as(format="png"))
            else:
                link = str(ctx.message.attachments[0].url)

        async with ctx.typing():
            try:
                async with self.session.get(link) as resp:
                    if resp.status != 200:
                        await ctx.send(
                            "Something went wrong when trying to get the image."
                        )
                        return
                    img = await resp.read()
                    img = BytesIO(img)
                    img.seek(0)
            except Exception:
                await ctx.send("Something went wrong when trying to get the image.")
                return

            await ctx.send(
                file=await self.bot.loop.run_in_executor(
                    None, self.get_color_palette, img
                )
            )
