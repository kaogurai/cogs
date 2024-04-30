from io import BytesIO
from typing import Optional

import colorgram
import discord
from PIL import Image, ImageDraw
from redbot.core import commands
from redbot.core.commands import Context

from .abc import MixinMeta


class ImageMixin(MixinMeta):
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @commands.command(aliases=["ship", "lovecalc"])
    async def lovecalculator(
        self,
        ctx: Context,
        user: discord.User,
        other_user: Optional[discord.User] = None,
    ):
        """
        Calculates the amount of love between two users.
        """
        if other_user is None:
            other_user = ctx.author
        love = (user.id + other_user.id) % 100
        user_avatar = user.display_avatar.with_format("png").url
        other_user_avatar = other_user.display_avatar.with_format("png").url

        e = discord.Embed(
            color=await ctx.embed_color(),
            title=f"{user.name} and {other_user.name} have {love}% compatibility.",
        )
        e.set_image(
            url=f"https://api.martinebot.com/v1/imagesgen/ship?percent={love}&first_user={user_avatar}&second_user={other_user_avatar}&no_69_percent_emoji=false"
        )
        e.set_footer(text="Powered by api.martinebot.com")
        await ctx.send(embed=e)

    def _get_color_palette(self, img: BytesIO) -> discord.File:
        """
        Creates a color palette from a given image.

        Credits to Flare for writing this code.
        """
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
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    async def palette(self, ctx: Context, link: Optional[str] = None, sorted=False):
        """
        Get the color palette of an image.

        By default it is sorted by prominence, but you can sort it by rgb by passing true.

        Thanks flare for making this!
        """
        if not link:
            if not ctx.message.attachments:
                link = ctx.author.display_avatar.with_format("png").url
            else:
                link = ctx.message.attachments[0].url

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
                    None, self._get_color_palette, img
                )
            )
