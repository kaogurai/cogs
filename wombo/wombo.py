import asyncio
import contextlib
from enum import Enum
from io import BytesIO

import aiohttp
import discord
from redbot.core import commands
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate


class Styles(Enum):
    SYNTHWAVE = 1
    UKIYOE = 2
    NONE = 3
    STEAMPUNK = 4
    FANTASY = 5
    VIBRANT = 6
    HD = 7
    PASTEL = 8
    PSYCHIC = 9
    DARKFANTASY = 10
    MYSTICAL = 11
    FESTIVE = 12
    BAROQUE = 13
    ETCHING = 14
    SDALI = 15
    WUHTERCUHLER = 16
    PROVENANCE = 17
    ROSEGOLD = 18
    MOONWALKER = 19
    BLACKLIGHT = 20


class Wombo(commands.Cog):
    """
    Generate incredible art using AI.
    """

    __version__ = "1.1.5"

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
        style = style.upper()
        enum = getattr(Styles, style)
        if enum:
            return enum.value

    async def check_nsfw(self, link):
        params = {"url": link}
        async with self.session.get(
            "https://api.kaogurai.xyz/v1/nsfwdetection/image", params=params
        ) as req:
            if req.status == 200:
                resp = await req.json()
                if "error" in resp.keys():
                    return False
                results = resp["safeSearchAnnotation"]
                is_nsfw = ["POSSIBLE", "LIKELY", "VERY_LIKELY"]
                if results["adult"] in is_nsfw or results["racy"] in is_nsfw:
                    return True
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

        for x in range(25):
            async with self.session.get(
                f"https://app.wombo.art/api/tasks/{session_id}", headers=headers
            ) as req:
                if req.status not in [200, 304]:
                    return

                resp = await req.json()
                if resp["result"]:
                    return resp["result"]["final"]

            await asyncio.sleep(3)

    @commands.command(aliases=["draw", "aiart"], usage="<text> [--style <style>]")
    async def wombo(self, ctx, *, text: str):
        """
        Generate art using AI.

        Possible styles:
        synthwave, ukiyoe, none, steampunk, fantasy, vibrant, hd, pastel, psychic, darkfantasy, mystical, festive, baroque, etching, sdali, wuhtercuhler, provenance, rosegold, moonwalker, blacklight
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

            async with self.session.get(link) as req:
                if req.status != 200:
                    await ctx.send("Something went wrong when downloading the image.")
                    return
                data = await req.read()

            vfile = BytesIO(data)
            vfile.seek(0)
            file = discord.File(vfile, filename="result.jpg")

            embed = discord.Embed(title="Here's your art!", color=await ctx.embed_color())
            embed.set_image(url="attachment://result.jpg")

            if not ctx.channel.is_nsfw():
                is_nsfw = await self.check_nsfw(link)
                if is_nsfw:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()

                    m = await ctx.send(
                        f"{ctx.author.mention}, this image may contain NSFW content. Would you like me to DM you the image?"
                    )
                    start_adding_reactions(m, ReactionPredicate.YES_OR_NO_EMOJIS)
                    pred = ReactionPredicate.yes_or_no(m, ctx.author)
                    try:
                        await ctx.bot.wait_for("reaction_add", check=pred, timeout=60)
                    except asyncio.TimeoutError:
                        with contextlib.suppress(discord.NotFound):
                            await m.delete()
                        return
                    if pred.result is True:
                        with contextlib.suppress(discord.NotFound):
                            await m.edit(
                                content=f"{ctx.author.mention}, sending image..."
                            )
                        try:
                            await ctx.author.send(embed=embed, file=file)
                        except discord.Forbidden:
                            await ctx.send(
                                "Failed to send image. Please make sure you have DMs enabled."
                            )
                        return
                    else:
                        with contextlib.suppress(discord.NotFound):
                            await m.delete()
                        return

            with contextlib.suppress(discord.NotFound):
                await m.delete()

            await ctx.send(embed=embed, file=file)
