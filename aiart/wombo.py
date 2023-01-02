import asyncio
import base64
import contextlib
from io import BytesIO
from typing import Optional

import discord
from PIL import Image
from redbot.core import commands
from redbot.core.commands import BadArgument, Context, Converter
from redbot.core.utils.chat_formatting import humanize_list
from thefuzz import process

from .abc import MixinMeta
from .utils import NoExitParser

# A lot of the code for parsing the arguments is inspired by flare's giveaways cog


class WomboConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> int:
        argument = argument.replace("—", "--")  # For iOS's weird smart punctuation

        parser = NoExitParser(add_help=False)
        parser.add_argument("prompt", type=str, nargs="*")
        parser.add_argument("--styles", action="store_true")
        parser.add_argument("--style", type=str, default=["Realistic"], nargs="*")
        parser.add_argument("--image", type=str, default=None, nargs="?")

        try:
            values = vars(parser.parse_args(argument.split(" ")))
        except Exception:
            raise BadArgument()

        if not values["prompt"] and not values["styles"]:
            raise BadArgument()

        values["prompt"] = " ".join(values["prompt"])

        if len(values["prompt"]) > 100 and not values["styles"]:
            raise BadArgument("The prompt needs to be 100 characters or less.")

        styles = await ctx.cog._get_wombo_styles()

        if values["styles"]:
            embed = discord.Embed(
                title="Available styles",
                description=humanize_list(list(styles.keys())),
                color=await ctx.embed_color(),
            )
            await ctx.send(embed=embed)
            return

        values["style"] = styles[
            process.extract(" ".join(values["style"]), list(styles.keys()), limit=1)[0][
                0
            ]
        ]

        if not values["image"] and ctx.message.attachments:
            values["image"] = ctx.message.attachments[0].url

        return values


class WomboCommand(MixinMeta):
    async def _get_wombo_styles(self) -> dict:
        async with self.session.get("https://paint.api.wombo.ai/api/styles") as req:
            if req.status == 200:
                return {
                    style["name"]: style["id"]
                    for style in await req.json()
                    if not style["is_premium"]
                }

    async def _get_wombo_media_id(self, token: str, data: bytes) -> Optional[str]:
        try:
            image = Image.open(BytesIO(data))
        except Exception:
            return

        headers = {
            "Authorization": f"Bearer {token}",
            "service": "Dream",
        }
        post_data = {
            "media_suffix": image.format,
            "media_expiry": "HOURS_72",
            "num_uploads": 1,
        }
        async with self.session.post(
            "https://mediastore.api.wombo.ai/io/", json=post_data, headers=headers
        ) as req:
            if req.status != 200:
                return
            resp = await req.json()
            media_id = resp[0]["id"]
            upload_url = resp[0]["media_url"]

        async with self.session.put(upload_url, data=data) as req:
            if req.status == 200:
                return media_id

    async def _get_wombo_image_link(
        self,
        token: str,
        style: str,
        text: str,
        *,
        input_image: Optional[str] = None,
    ) -> Optional[str]:
        params = {
            "input_spec": {
                "display_freq": 1,
                "prompt": text,
                "style": style,
                "gen_type": "NORMAL",
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
        async with self.session.post(
            f"https://paint.api.wombo.ai/api/v2/tasks",
            json=params,
            headers=headers,
        ) as req:
            if req.status != 200:
                return
            resp = await req.json()

        session_id = resp["id"]

        for x in range(25):
            params = {
                "ids": session_id,
            }
            async with self.session.get(
                f"https://paint.api.wombo.ai/api/v2/tasks/batch",
                headers=headers,
                params=params,
            ) as req:
                if req.status not in [200, 304]:
                    return

                resp = (await req.json())[0]

                if resp["state"] == "failed":
                    return

                if resp["result"]:
                    return resp["result"]["final"]

            await asyncio.sleep(3)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def wombo(self, ctx: Context, *, arguments: WomboConverter):
        """
        Generate art using Wombo.

        You can use the following arguments (all are optional):
        `--style`: The style of art to generate. Defaults to `Realistic`. Run `[p]wombo --styles` to see a list of styles.
        `--image`: The image to use as input. If not provided, the first image attached to the message will be used.
        """
        if not arguments:
            return  # This should mean that the user ran `[p]wombo --styles`

        m = await ctx.reply("Generating art... This may take a while.")
        async with ctx.typing():
            token = await self._get_firebase_bearer_token(
                "AIzaSyDCvp5MTJLUdtBYEKYWXJrlLzu1zuKM6Xw"
            )
            if not token:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.reply("Failed to generate art. Please try again later.")
                return

            media_id = None
            if arguments["image"]:
                async with self.session.get(arguments["image"]) as req:
                    if req.status == 200:
                        media_id = await self._get_wombo_media_id(
                            token, await req.read()
                        )

            link = await self._get_wombo_image_link(
                token,
                arguments["style"],
                arguments["prompt"],
                input_image=media_id,
            )

            if not link:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.reply(
                    "Failed to generate art. Please try again later. Usually this is caused by triggering Wombo's NSFW filter."
                )
                return

            with contextlib.suppress(discord.NotFound):
                await m.delete()

            async with self.session.get(link) as req:
                if req.status != 200:
                    await ctx.reply(f"Something went wrong when downloading the image.")
                    return
                data = await req.read()

        await self.send_images(ctx, [data])
