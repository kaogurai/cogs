import asyncio
import random
from io import BytesIO
from typing import Optional

import discord
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
                    await asyncio.sleep(2)
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
    async def ocr(self, ctx, image_url: Optional[str], lang: str = "english"):
        """
        Convert an image to text.

        You can either upload an image or provide a direct link.

        Supported formats: jpg, png, webp, pdf

        You can also specify the language for more accurate results.

        Supported languages: arabic, bulgarian, chinesesimplified, chinesetraditional, croatian, czech, danish, dutch, english, finnish, french, german, greek, hungarian, italian, japanese, korean, polish, portuguese, russian, slovenian, spanish, swedish, and turkish
        """
        if not image_url and not ctx.message.attachments:
            await ctx.send("Please provide an image to convert to text.")
            return

        if ctx.message.attachments:
            link = ctx.message.attachments[0].url
            lang = image_url or "english"
        else:
            link = image_url

        dot_split = link.split(".")[-1]
        filetype = dot_split.split("?")[0]
        if filetype not in ["jpg", "png", "webp", "pdf"]:
            await ctx.send("Sorry, that format is not supported.")
            return

        langs = {
            "arabic": "ara",
            "bulgarian": "bul",
            "chinesesimplified": "chs",
            "chinesetraditional": "cht",
            "croatian": "hrv",
            "czech": "cze",
            "danish": "dan",
            "dutch": "dut",
            "english": "eng",
            "finnish": "fin",
            "french": "fre",
            "german": "ger",
            "greek": "gre",
            "hungarian": "hun",
            "italian": "ita",
            "japanese": "jpn",
            "korean": "kor",
            "polish": "pol",
            "portuguese": "por",
            "russian": "rus",
            "slovenian": "slv",
            "spanish": "spa",
            "swedish": "swe",
            "turkish": "tur",
        }

        if lang.lower() not in langs.keys():
            await ctx.send(
                "Sorry, that language is not supported.\n\nSupported languages: {}".format(
                    ", ".join(langs.keys())
                )
            )
            return

        async with ctx.typing():
            async with self.session.post(
                "https://api.ocr.space/parse/image",
                data={
                    "apikey": "5a64d478-9c89-43d8-88e3-c65de9999580",  # Extracted from the web client
                    "language": langs[lang.lower()],
                    "detectOrientation": "true",
                    "isOverlayRequired": "false",
                    "scale": "true",
                    "url": link,
                },
            ) as resp:
                if resp.status != 200:
                    await ctx.send("Something went wrong when trying to get the text.")
                    return
                data = await resp.json()

        if data["IsErroredOnProcessing"]:
            await ctx.send("Sorry, the OCR backend isn't working correctly.")
            return

        results = data["ParsedResults"][0]["ParsedText"]
        if results != "":
            embed = discord.Embed(
                title="OCR Results",
                color=await ctx.embed_color(),
                description=results[:4000],
                url=link,
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("No text was found.")
