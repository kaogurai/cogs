import asyncio
import contextlib
import time
from io import BytesIO
from typing import Optional

import discord
from PIL import Image
from rapidfuzz import process
from redbot.core import commands
from redbot.core.commands import BadArgument, Context, Converter
from redbot.core.utils.chat_formatting import humanize_list

from .abc import MixinMeta
from .utils import NoExitParser

# A lot of the code for parsing the arguments is inspired by flare's giveaways cog


class WomboConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> int:
        argument = argument.replace("—", "--")  # For iOS's weird smart punctuation

        parser = NoExitParser(add_help=False)
        parser.add_argument("prompt", type=str, nargs="*")
        parser.add_argument("--styles", action="store_true")
        parser.add_argument("--style", type=str, default=["Realistic v2"], nargs="*")
        parser.add_argument("--image", type=str, default=None, nargs="?")
        parser.add_argument("--image-weight", type=float, default=0.5, nargs="?")

        parser.add_argument(
            "--amount",
            type=int,
            default=4 if ctx.cog.wombo_data["api_token"] else 2,
            nargs="?",
        )

        # Wombo API only
        parser.add_argument("--height", type=int, default=1024, nargs="?")
        parser.add_argument("--width", type=int, default=1024, nargs="?")
        parser.add_argument("--seed", type=int, default=None, nargs="?")
        parser.add_argument("--steps", type=int, default=40, nargs="?")
        parser.add_argument(
            "-n", "--negative", "--negative-prompt", type=str, default=[""], nargs="*"
        )
        parser.add_argument("--text-cfg", type=float, default=7, nargs="?")

        try:
            values = vars(parser.parse_args(argument.split(" ")))
        except Exception:
            raise BadArgument()

        if not values["prompt"] and not values["styles"]:
            raise BadArgument()

        values["prompt"] = " ".join(values["prompt"])
        values["negative"] = " ".join(values["negative"])

        if values["amount"] not in range(1, 10):
            raise BadArgument("The amount needs to be between 1 and 9.")

        if (
            not ctx.cog.wombo_data["api_token"]
            and len(values["prompt"]) > 200
            and not values["styles"]
        ):
            raise BadArgument("The prompt needs to be 200 characters or less.")

        # Image weight is a number between 0 and 1, inclusive
        if not 0 <= values["image_weight"] <= 1:
            raise BadArgument("The image weight needs to be between 0 and 1.")

        # Steps is a number between 1 and 100, inclusive
        if not 20 <= values["steps"] <= 50:
            raise BadArgument("The steps needs to be between 20 and 50.")

        # Text cfg is a number between 0 and 10, inclusive
        if not 1 <= values["text_cfg"] <= 30:
            raise BadArgument("The text cfg needs to be between 1 and 30.")

        # Height and width are numbers between 1 and 10,000, inclusive
        if not 1 <= values["height"] <= 10000:
            raise BadArgument("The height needs to be between 1 and 10,000.")

        if not 1 <= values["width"] <= 10000:
            raise BadArgument("The width needs to be between 1 and 10,000.")

        if (
            values["seed"] is not None
            or (values["width"] * values["height"]) > 35000000
        ):
            values["amount"] = 1

        styles = await ctx.cog._get_wombo_styles()
        if not styles:
            raise BadArgument("Something went wrong while getting the styles.")

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
    async def _get_wombo_app_token(self) -> Optional[str]:
        if (
            self.wombo_data["app_token"]
            and self.wombo_data["app_token_expires"] > time.time()
        ):
            return self.wombo_data["app_token"]

        # Yes, I am aware that we could just refresh the token
        # But, for rate limiting purposes, it's better to just get a new one
        new_token = await self._get_firebase_bearer_token(
            "AIzaSyDCvp5MTJLUdtBYEKYWXJrlLzu1zuKM6Xw"
        )

        if new_token:
            self.wombo_data["app_token"] = new_token
            self.wombo_data["app_token_expires"] = (
                time.time() + 3500
            )  # It's actually 3600, but we still need time to get the image

        return new_token

    async def _get_wombo_app_styles(self) -> Optional[dict]:
        async with self.session.get("https://paint.api.wombo.ai/api/styles") as req:
            if req.status == 200:
                return {
                    style["name"]: style["id"]
                    for style in await req.json()
                    if not style["is_premium"]
                }

    async def _get_wombo_api_styles(self) -> Optional[dict]:
        headers = {
            "Authorization": f"bearer {self.wombo_data['api_token']}",
        }
        async with self.session.get(
            "https://api.luan.tools/api/styles/", headers=headers
        ) as req:
            if req.status == 200:
                return {style["name"]: style["id"] for style in await req.json()}

    async def _get_wombo_styles(self) -> Optional[dict]:
        if self.wombo_data["api_token"]:
            return await self._get_wombo_api_styles()
        else:
            return await self._get_wombo_app_styles()

    async def _get_wombo_app_media_id(self, token: str, data: bytes) -> Optional[str]:
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

    async def _get_wombo_app_image_link(self, arguments: dict) -> Optional[str]:
        token = await self._get_wombo_app_token()
        if not token:
            return

        media_id = None
        if arguments["image"]:
            async with self.session.get(arguments["image"]) as req:
                if req.status == 200:
                    media_id = await self._get_wombo_app_media_id(
                        token, await req.read()
                    )

        params = {
            "input_spec": {
                "display_freq": 1,
                "prompt": arguments["prompt"],
                "style": arguments["style"],
                "gen_type": "NORMAL",
            }
        }
        if media_id:
            params["input_spec"]["input_image"] = {
                "weight": "MEDIUM",
                "mediastore_id": media_id,
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

    async def _get_wombo_api_image_link(self, arguments: dict) -> Optional[str]:
        headers = {
            "Authorization": f"bearer {self.wombo_data['api_token']}",
        }
        data = {
            "use_target_image": bool(arguments["image"]),
        }
        async with self.session.post(
            "https://api.luan.tools/api/tasks/", headers=headers, json=data
        ) as req:
            if req.status != 200:
                return
            resp = await req.json()
            task_id = resp["id"]

        if arguments["image"]:
            async with self.session.get(arguments["image"]) as req:
                if req.status == 200:
                    resp["target_image_url"]["fields"]["file"] = await req.read()
                    async with self.session.post(
                        resp["target_image_url"]["url"],
                        data=resp["target_image_url"]["fields"],
                    ):
                        pass

        data = {
            "input_spec": {
                "style": arguments["style"],
                "prompt": arguments["prompt"],
                "target_image_weight": 0.5,
                "width": arguments["width"],
                "height": arguments["height"],
                "allow_nsfw": True,
                "has_watermark": False,
                "steps": arguments["steps"],
                "text_cfg": arguments["text_cfg"],
                "negative_prompt": arguments["negative"],
                "seed": arguments["seed"],
            }
        }
        async with self.session.put(
            "https://api.luan.tools/api/tasks/" + task_id, headers=headers, json=data
        ) as req:
            if req.status != 200:
                return

        for x in range(25):
            async with self.session.get(
                "https://api.luan.tools/api/tasks/" + task_id, headers=headers
            ) as req:
                if req.status != 200:
                    return
                resp = await req.json()

                if resp["state"] == "failed":
                    return
                elif resp["state"] == "completed":
                    return resp["result"]
                else:
                    await asyncio.sleep(3)

    @commands.command(aliases=["draw", "text2art", "text2img", "text2image"])
    @commands.bot_has_permissions(embed_links=True)
    async def wombo(self, ctx: Context, *, arguments: WomboConverter):
        """
        Generate art using Wombo.

        If you would like to view the styles available, run `[p]wombo --styles`.

        **Arguments:**
            `prompt` The prompt to use for the art.
            `--style` The style to use for the art. Defaults to `Realistic v2`.
            `--image` The image to use for the art. You can also upload an attachment instead of using this argument.
            `--amount` The amount of images to generate.

            If the bot owner has set the Wombo API key, these parameters are also available:

            `--width` The width of the art. Defaults to 1024. Range is 100-10000
            `--height` The height of the art. Defaults to 1024. Range is 100-10000
            `--steps` The amount of steps to use for the art. Defaults to 40. Range is 20-50.
            `--text-cfg` The text cfg value to use for the art. Defaults to 7.5. Range is 1-30.
            `--negative` The negative prompt to use for the art. Defaults to `None`.
            `--seed` The seed to use for the art. Defaults to `None`.

            **Note: If the total amount of pixels is greater than 35,000,000, it will return one image.**

        """
        if not arguments:
            return  # This should mean that the user ran `[p]wombo --styles`

        m = await ctx.reply("Generating art... This may take a while.")
        async with ctx.typing():

            tasks = []
            for x in range(arguments["amount"]):
                if not self.wombo_data["api_token"]:
                    task = self._get_wombo_app_image_link(arguments)
                else:
                    task = self._get_wombo_api_image_link(arguments)

                tasks.append(asyncio.create_task(task))

            if not self.wombo_data["api_token"]:
                # This is so if the token is expired, it will get refreshed here instead of every task needing to do it.
                await self._get_wombo_app_token()

            links = [x for x in await asyncio.gather(*tasks) if x]

            with contextlib.suppress(discord.NotFound):
                await m.delete()

            if not links:
                await ctx.reply("Something went wrong when generating the art.")
                return

            images = []
            tasks = []
            for link in links:
                if not link:
                    continue

                tasks.append(asyncio.create_task(self.get_image(link)))

            images = await asyncio.gather(*tasks)

        await self.send_images(ctx, [x for x in images if x])

    @commands.command(aliases=["enhanceprompt", "betterprompt"])
    async def magicprompt(self, ctx: Context, *, prompt: str):
        """
        Generate a prompt using MagicPrompt.

        **Arguments:**
            `prompt` The prompt to enhance.
        """
        async with ctx.typing():
            token = await self._get_wombo_app_token()
            if not token:
                await ctx.reply("Something went wrong when getting the token.")
                return

            headers = {
                "Authorization": f"bearer {token}",
            }
            params = {
                "prompt": prompt,
            }
            async with self.session.get(
                "https://paint.api.wombo.ai/api/prompt/suggestion/",
                headers=headers,
                params=params,
            ) as req:
                if req.status != 200:
                    await ctx.reply("Something went wrong when getting the prompt.")
                    return
                resp = await req.json()

            embed = discord.Embed(
                title="MagicPrompt",
                description=resp["suggestion"],
                color=await ctx.embed_color(),
            )
            await ctx.reply(embed=embed)
