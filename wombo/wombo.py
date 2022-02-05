import asyncio
import contextlib
import json

import aiohttp
import discord
from redbot.core import commands


class Wombo(commands.Cog):
    """
    Generate incredible art using AI.
    """

    __version__ = "1.0.9"

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    def get_style(self, style):
        styles = {
            "synthwave": 1,
            "ukiyoe": 2,
            "none": 3,
            "steampunk": 4,
            "fantasy": 5,
            "vibrant": 6,
            "hd": 7,
            "pastel": 8,
            "psychic": 9,
            "darkfantasy": 10,
            "mystical": 11,
            "festive": 12,
            "baroque": 13,
            "etching": 14,
            "sdali": 15,
            "wuhtercuhler": 16,
            "provenance": 17,
            "rosegold": 18,
        }

        style = style.lower()
        if style in styles:
            return styles[style]

    async def check_nsfw(self, link):
        params = {"url": link}
        try:
            async with self.session.get(
                "http://api.rest7.com/v1/detect_nudity.php", params=params
            ) as req:
                if req.status == 200:
                    resp = await req.text()
                    resp = json.loads(resp)
                    if "nudity_percentage" in resp:
                        return resp["nudity_percentage"] > 0.5
        except aiohttp.ClientError:
            pass
        return False

    async def get_bearer_token(self):
        params = {"key": "AIzaSyDCvp5MTJLUdtBYEKYWXJrlLzu1zuKM6Xw"}
        data = {"returnSecureToken": True}
        async with self.session.post(
            "https://identitytoolkit.googleapis.com/v1/accounts:signUp",
            json=data,
            params=params,
        ) as req:
            if req.status == 200:
                resp = await req.json()
                return resp["idToken"]

    async def create_session(self, token: str):
        token = await self.get_bearer_token()
        if not token:
            return
        headers = {
            "authorization": f"bearer {token}",
            "content-type": "text/plain;charset=UTF-8",
        }
        data = {"premium": False}
        async with self.session.post(
            "https://app.wombo.art/api/tasks", json=data, headers=headers
        ) as req:
            if req.status == 200:
                resp = await req.json()
                return resp

    async def get_image_link(self, token, session_id, style, text):
        params = {
            "input_spec": {
                "display_freq": 1,
                "prompt": text,
                "style": style,
            }
        }
        headers = {
            "authorization": f"bearer {token}",
            "content-type": "text/plain;charset=UTF-8",
        }
        async with self.session.put(
            f"https://app.wombo.art/api/tasks/{session_id}", json=params, headers=headers
        ) as req:
            if req.status != 200:
                return

            resp = await req.json()

        while True:
            async with self.session.get(
                f"https://app.wombo.art/api/tasks/{session_id}", headers=headers
            ) as req:
                if req.status not in [200, 304]:
                    return

                resp = await req.json()
                if resp["result"]:
                    return resp["result"]["final"]

            await asyncio.sleep(1.5)

    @commands.command(aliases=["draw", "aiart"], usage="<text> [--style <style>]")
    async def wombo(self, ctx, *, text: str):
        """
        Generate art using AI.

        Possible styles:
        synthwave, ukiyoe, none, steampunk, fantasy, vibrant, hd, pastel, psychic, darkfantasy, mystical, festive, baroque, etching, sdali, wuhtercuhler, provenance, rosegold
        """
        if len(text) > 100:
            await ctx.send("The text needs to be 100 characters or less.")
            return

        text = text.replace("—", "--")
        args = text.split("--style")
        if len(args) == 1:
            style = "none"
            text = args[0]
        else:
            style = args[1].strip()
            text = args[0].strip()
            if text == "":
                await ctx.send("You need to specify text to draw.")
                return

        style = self.get_style(style)
        if not style:
            await ctx.send("Invalid style.")
            return

        m = await ctx.send("Generating art... This may take a while.")
        async with ctx.typing():
            token = await self.get_bearer_token()
            if not token:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.send("Failed to generate art. Please try again later.")
                return
            session = await self.create_session(token)
            if not session:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.send("Failed to generate art. Please try again later.")
                return
            link = await self.get_image_link(token, session["id"], style, text)
            if not link:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.send("Failed to generate art. Please try again later.")
                return

            if not ctx.channel.is_nsfw():
                is_nsfw = await self.check_nsfw(link)
                if is_nsfw:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
                    try:
                        await m.edit(content="This channel is not NSFW.")
                    except discord.NotFound:
                        await ctx.send("This channel is not NSFW.")
                    return

            embed = discord.Embed(title="Here's your art!", color=await ctx.embed_color())
            embed.set_image(url=link)
            try:
                await m.edit(content=None, embed=embed)
            except discord.NotFound:
                await ctx.send(embed=embed)
