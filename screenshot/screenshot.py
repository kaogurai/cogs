from redbot.core import commands, Config, checks
from pyppeteer import launch
import pyppeteer
import discord
import asyncio
import io

class Screenshot(commands.Cog):
    """Screenshots a given link."""
    
    @commands.bot_has_permissions(attach_files=True)
    @commands.command()
    @commands.is_owner()
    async def screenshot(self, ctx, link: str, wait: int = 0):
        """Screenshots a given link."""
        if link.startswith('https://'):
            pass
        else:
            if link.startswith('http://'):
                pass
            else: 
                await ctx.send("That doesn't look like a valid link!")
                return
            
        browser = await launch()
        page = await browser.newPage()
        try:
            await page.goto(link)
        except pyppeteer.page.PageError:
            await ctx.send("Sorry, I couldn't find anything at that link!")
            await browser.close()
            return
        await asyncio.sleep(wait)
        result = await page.screenshot()
        await browser.close()
        f = io.BytesIO(result)
        file = discord.File(f, filename="screenshot.png")
        await ctx.send(file=file)