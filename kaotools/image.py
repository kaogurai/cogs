import asyncio
from io import BytesIO
from typing import Optional

import colorgram
import discord
from PIL import Image, ImageDraw
from redbot.core import commands

from .abc import MixinMeta


class ImageMixin(MixinMeta):
    @commands.command()
    @commands.bot_has_permissions(attach_files=True)
    async def obama(self, ctx, *, text: str):
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
                    await asyncio.sleep(2)  # Needs some more time to generate, I guess
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
    async def lovecalculator(self, ctx, user: discord.User, user2: discord.User = None):
        """
        Calculates the amount of love between two users.
        """
        if user2 is None:
            user2 = ctx.author
        love = (user.id + user2.id) % 100
        ua = user.avatar_url_as(static_format="png")
        u2a = user2.avatar_url_as(static_format="png")
        u = f"https://api.martinebot.com/v1/imagesgen/ship?percent={love}&first_user={ua}&second_user={u2a}&no_69_percent_emoji=false"
        t = f"{user.name} and {user2.name} have {love}% compatibility."
        e = discord.Embed(color=await ctx.embed_color(), title=t)
        e.set_image(url=u)
        e.set_footer(text="Powered by api.martinebot.com")
        await ctx.send(embed=e)

    @commands.command()
    async def ocr(self, ctx, link: Optional[str] = None):
        """
        Convert an image to text.

        You can either upload an image or provide a direct link.

        Supported formats: jpg, png, webp, gif, bmp, raw, ico
        """
        if not link and not ctx.message.attachments:
            await ctx.send("Please provide an image to convert to text.")
            return

        if not link:
            link = str(ctx.message.attachments[0].url)

        async with ctx.typing():
            async with self.session.get(
                f"{self.KAO_API_URL}/ocr/image",
                params={
                    "url": link,
                },
            ) as resp:
                if resp.status != 200:
                    await ctx.send("Something went wrong when trying to get the text.")
                    return
                data = await resp.json()

        if not data:
            await ctx.send("No text was found.")
            return

        if "error" in data.keys():
            await ctx.send(data["error"]["message"])
            return

        results = data["fullTextAnnotation"]["text"]
        embed = discord.Embed(
            title="OCR Results",
            color=await ctx.embed_color(),
            description=results[:4000],
            url=link,
        )
        await ctx.send(embed=embed)

    def get_color_palette(self, img):
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
    async def palette(self, ctx, link: Optional[str] = None, sorted=False):
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
