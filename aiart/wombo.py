import asyncio
import base64
import contextlib
from io import BytesIO
from typing import Optional

import discord
from PIL import Image
from redbot.core import commands
from redbot.core.commands import Context
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

from .abc import MixinMeta

WOMBO_STYLES = {
    "realistic": 32,
    "throwback": 35,
    "malevolent": 40,
    "none": 3,
    "ghibli": 22,
    "melancholic": 28,
    "provenance": 17,
    "arcane": 34,
    "radioactive": 27,
    "rosegold": 18,
    "blacklight": 20,
    "wuhtercuhler": 16,
    "sdali": 15,
    "etching": 14,
    "baroque": 13,
    "mystical": 11,
    "darkfantasy": 10,
    "hd": 7,
    "vibrant": 6,
    "fantasy": 5,
    "steampunk": 4,
    "psychic": 9,
    "psychedelic": 21,
    "ukiyoe": 2,
    "synthwave": 1,
}


class WomboCommand(MixinMeta):
    """
    Implements the Internal WOMBO API used in their web client.
    """

    async def _get_wombo_bearer_token(self) -> Optional[str]:
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

    async def _create_wombo_session(self, token: str) -> Optional[str]:
        headers = {
            "authorization": f"bearer {token}",
            "content-type": "text/plain;charset=UTF-8",
        }
        data = {"premium": False}
        async with self.session.post(
            "https://paint.api.wombo.ai/api/tasks", json=data, headers=headers
        ) as req:
            if req.status == 200:
                resp = await req.json()
                return resp["id"]

    async def _get_wombo_media_id(self, token: str, data: bytes) -> Optional[str]:
        try:
            image = Image.open(BytesIO(data))
        except Exception:
            return

        headers = {
            "authorization": f"bearer {token}",
            "content-type": "text/plain;charset=UTF-8",
        }
        data = {
            "media_suffix": image.format,
            "num_uploads": 1,
            "image": base64.b64encode(data).decode("utf-8"),
        }
        async with self.session.post(
            "https://app.wombo.art/api/mediastore", json=data, headers=headers
        ) as req:
            if req.status == 200:
                resp = await req.json()
                return resp["mediastore_uid"]

    async def _get_wombo_image_link(
        self, token: str, session_id: str, style: str, text: str, *, input_image: Optional[str] = None
    ) -> Optional[str]:
        params = {
            "input_spec": {
                "display_freq": 1,
                "prompt": text,
                "style": style,
            }
        }
        if input_image:
            params["input_spec"]["input_image"] = {
                "weight": "HIGH",
                "mediastore_id": input_image,
            }

        headers = {
            "authorization": f"bearer {token}",
            "content-type": "text/plain;charset=UTF-8",
        }
        async with self.session.put(
            f"https://paint.api.wombo.ai/api/tasks/{session_id}",
            json=params,
            headers=headers,
        ) as req:
            if req.status != 200:
                return
            resp = await req.json()

        for x in range(25):
            async with self.session.get(
                f"https://paint.api.wombo.ai/api/tasks/{session_id}", headers=headers
            ) as req:
                if req.status not in [200, 304] or resp["state"] == "failed":
                    return

                resp = await req.json()
                if resp["result"]:
                    return resp["result"]["final"]

            await asyncio.sleep(3)

    @commands.command(usage="<text> [--style <style>]", help="Generate art using AI\n\nPossible styles: " + ", ".join(WOMBO_STYLES))
    @commands.bot_has_permissions(embed_links=True)
    async def wombo(self, ctx: Context, *, text: str):
        if len(text) > 100:
            await ctx.send("The text needs to be 100 characters or less.")
            return

        text = text.replace("—", "--")
        args = text.split("--style")
        if len(args) == 1:
            style = "realistic"
            text = args[0]
        else:
            style = args[1].strip()
            text = args[0].strip()
            if text == "":
                await ctx.send_help()
                return

        style = WOMBO_STYLES.get(style.lower())
        if not style:
            await ctx.send(
                f"Invalid style. Possible styles: {', '.join(WOMBO_STYLES.keys())}"
            )
            return

        m = await ctx.send("Generating art... This may take a while.")
        async with ctx.typing():
            token = await self._get_wombo_bearer_token()
            if not token:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.send("Failed to generate art. Please try again later.")
                return
            session_id = await self._create_wombo_session(token)
            if not session_id:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.send("Failed to generate art. Please try again later.")
                return

            media_id = None
            if ctx.message.attachments:
                data = await ctx.message.attachments[0].read()
                media_id = await self._get_wombo_media_id(token, data)

            link = await self._get_wombo_image_link(
                token, session_id, style, text, input_image=media_id
            )

            if not link:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.send(
                    "Failed to generate art. Please try again later. Usually this is caused by triggering Wombo's NSFW filter."
                )
                return

            async with self.session.get(link) as req:
                if req.status != 200:
                    await ctx.send(f"Something went wrong when downloading the image.")
                    return
                data = await req.read()

            vfile = BytesIO(data)
            vfile.seek(0)
            file = discord.File(vfile, filename="result.jpg")

            embed = discord.Embed(title="Here's your art!", color=await ctx.embed_color())
            embed.set_image(url="attachment://result.jpg")

            if ctx.guild and not ctx.channel.is_nsfw():

                is_nsfw = await self.check_nsfw(data)
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

            await ctx.send(embed=embed, file=file, content=ctx.author.mention)
