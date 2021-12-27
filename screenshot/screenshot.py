import asyncio
import io

import discord
import pyppeteer
from pyppeteer import launch
from redbot.core import commands


class Screenshot(commands.Cog):
    """
    Screenshots a given link using pyppeteer.
    """

    __version__ = "1.0.0"

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    @commands.bot_has_permissions(attach_files=True)
    @commands.command(aliases=["ss"])
    @commands.is_owner()
    async def screenshot(self, ctx, link: str, wait: int = 3):
        """
        Screenshots a given link.
        If no time is given, it will wait 3 seconds to screenshot
        """

        await ctx.trigger_typing()
        browser = await launch()
        page = await browser.newPage()
        await page.setViewport({"width": 1280, "height": 720})
        try:
            await page.goto(link)
        except pyppeteer.page.PageError:
            await ctx.send("Sorry, I couldn't find anything at that link!")
            await browser.close()
            return
        except Exception:
            await ctx.send(
                "Sorry, I ran into an issue! Make sure to include http:// or https:// at the beginning of the link."
            )
            await browser.close()
            return

        await asyncio.sleep(wait)
        result = await page.screenshot()
        await browser.close()
        f = io.BytesIO(result)
        file = discord.File(f, filename="screenshot.png")
        await ctx.send(file=file)
