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
    async def ocr(self, ctx, image_url: Optional[str], lang: str = "eng"):
        """
        Convert an image to text.

        You can either upload an image or provide a direct link.

        Supported formats: jpg, png, webp

        You can also specify the language for more accurate results.

        Supported languages: afr, amh, ara, asm, aze, aze_cyrl, bel, ben, bod, bos, bre, bul, cat, ceb, ces, chi_sim, chi_sim_vert, chi_tra, chi_tra_vert, chr, cos, cym, dan, deu, div, dzo, ell, eng, enm, epo, est, eus, fao, fas, fil, fin, fra, frk, frm, fry, gla, gle, glg, grc, guj, hat, heb, hin, hrv, hun, hye, iku, ind, isl, ita, ita_old, jav, jpn, jpn_vert, kan, kat, kat_old, kaz, khm, kir, kmr, kor, kor_vert, lao, lat, lav, lit, ltz, mal, mar, mkd, mlt, mon, mri, msa, mya, nep, nld, nor, oci, ori, osd, pan, pol, por, pus, que, ron, rus, san, sin, slk, slv, snd, spa, spa_old, sqi, srp, srp_latn, sun, swa, swe, syr, tam, tat, tel, tgk, tha, tir, ton, tur, uig, ukr, urd, uzb, uzb_cyrl, vie, yid, yor
        """
        if not image_url and not ctx.message.attachments:
            await ctx.send("Please provide an image to convert to text.")
            return

        if ctx.message.attachments:
            link = ctx.message.attachments[0].url
            lang = image_url or "eng"
        else:
            link = image_url

        dot_split = link.split(".")[-1]
        filetype = dot_split.split("?")[0]
        if filetype not in ["jpg", "png", "webp"]:
            await ctx.send("Sorry, that format is not supported.")
            return

        async with self.session.get(f"{self.KAO_API_URL}/ocr/languages") as resp:
            if resp.status != 200:
                await ctx.send("Something went wrong when trying to get the languages.")
                return
            languages = await resp.json()

        if lang.lower() not in languages:
            await ctx.send(
                "Sorry, that language is not supported.\n\nSupported languages: {}".format(
                    ", ".join(languages)
                )
            )
            return

        async with self.session.get(link) as resp:
            if resp.status != 200:
                await ctx.send("Something went wrong when trying to get the image.")
                return
            res = await resp.read()

        async with ctx.typing():
            async with self.session.post(
                f"{self.KAO_API_URL}/ocr/image",
                data={
                    "file": res,
                },
                params={"lang": lang.lower()},
            ) as resp:
                if resp.status != 200:
                    await ctx.send("Something went wrong when trying to get the text.")
                    return
                data = await resp.json()

        results = data["text"]
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
