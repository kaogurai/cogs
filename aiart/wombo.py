import asyncio
import contextlib
from typing import Optional

import discord
from rapidfuzz import process
from redbot.core import commands
from redbot.core.commands import BadArgument, Context, Converter
from redbot.core.utils.chat_formatting import humanize_list

from .abc import MixinMeta
from .utils import NoExitParser


# Thanks for the inspiration on the parser, Flare
class WomboConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> dict:
        """
        The wombo command as a large amount of arguments, so a
        separate class that facilitates argparse-based arguments
        is needed.
        """

        # iOS usually converts a double dash into a longer single one
        # this reverts it so the parser works correctly
        argument = argument.replace("—", "--")

        parser = NoExitParser(add_help=False)
        parser.add_argument("prompt", type=str, nargs="*")
        parser.add_argument("--styles", action="store_true")
        parser.add_argument("--style", type=str, default=["Dreamland v3"], nargs="*")
        parser.add_argument("--image", type=str, default=None, nargs="?")
        parser.add_argument("--image-weight", type=float, default=0.5, nargs="?")
        parser.add_argument(
            "--amount",
            type=int,
            default=4,
            nargs="?",
        )
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

        # If amount of pixels are above 35,000,000, only one image is displayed
        if (
            values["seed"] is not None
            or (values["width"] * values["height"]) > 35000000
        ):
            values["amount"] = 1

        styles = await ctx.cog._get_wombo_api_styles()
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

        # Fuzzy search for closest style
        values["style"] = styles[
            process.extract(" ".join(values["style"]), list(styles.keys()), limit=1)[0][
                0
            ]
        ]

        if not values["image"] and ctx.message.attachments:
            values["image"] = ctx.message.attachments[0].url

        values["nsfw"] = ctx.channel.is_nsfw() if ctx.guild else True

        return values


class WomboCommand(MixinMeta):
    async def _get_wombo_api_styles(self) -> Optional[dict]:
        """
        Returns a dictionary of styles from the Wombo API.
        """
        headers = {
            "Authorization": f"bearer {self.api_token}",
        }
        async with self.session.get(
            "https://api.luan.tools/api/styles/", headers=headers
        ) as req:
            if req.status == 200:
                return {style["name"]: style["id"] for style in await req.json()}

    async def _get_wombo_api_image_link(self, arguments: dict) -> Optional[str]:
        """
        Returns a link to a generated image with the given arguments using the Wombo API.
        """
        headers = {
            "Authorization": f"bearer {self.api_token}",
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
                "allow_nsfw": arguments["nsfw"],
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
            `--style` The style to use for the art. Defaults to `Dreamland v3`.
            `--image` The image to use for the art. You can also upload an attachment instead of using this argument.
            `--amount` The amount of images to generate.
            `--width` The width of the art. Defaults to 1024. Range is 100-10000
            `--height` The height of the art. Defaults to 1024. Range is 100-10000
            `--steps` The amount of steps to use for the art. Defaults to 40. Range is 20-50.
            `--text-cfg` The text cfg value to use for the art. Defaults to 7.5. Range is 1-30.
            `--negative` The negative prompt to use for the art. Defaults to `None`.
            `--seed` The seed to use for the art. Defaults to `None`.

            **Note: If the total amount of pixels is greater than 35,000,000, it will return one image.**

        """
        # This should only happen when the user runs `[p]wombo --styles`
        # Therefore we don't need to send anything as it already has
        if not arguments:
            return

        m = await ctx.reply("Generating art... This may take a while.")
        async with ctx.typing():
            tasks = [
                self._get_wombo_api_image_link(arguments)
                for _ in range(arguments["amount"])
            ]
            links = [x for x in await asyncio.gather(*tasks) if x]

            with contextlib.suppress(discord.NotFound):
                await m.delete()

            if not links:
                await ctx.reply(
                    "Something went wrong when generating the art. You probably hit the NSFW filter, try again in a NSFW channel."
                )
                return

            images = []
            tasks = []
            for link in links:
                if not link:
                    continue

                tasks.append(asyncio.create_task(self._get_image(link)))

            images = await asyncio.gather(*tasks)

        await self._send_images(ctx, [x for x in images if x])
