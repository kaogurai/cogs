import asyncio
import contextlib
from typing import Optional

import discord
from redbot.core import commands
from redbot.core.commands import BadArgument, Context, Converter
from thefuzz import process

from .abc import MixinMeta
from .utils import NoExitParser

MAGE_ASPECTS = ["cinema", "landscape", "square", "tablet", "phone"]


class StableDiffusionArguments(Converter):
    async def convert(self, ctx: Context, argument: str) -> dict:
        argument = argument.replace("—", "--")  # For iOS's weird smart punctuation

        parser = NoExitParser(add_help=False)
        parser.add_argument("prompt", type=str, nargs="*")
        parser.add_argument(
            "--aspect", "--aspect-ratio", type=str, default="square", nargs="?"
        )
        parser.add_argument("--steps", type=int, default=50, nargs="?")
        parser.add_argument("--guidance", type=float, default=7.1, nargs="?")
        parser.add_argument("--seed", type=int, default=None, nargs="?")
        parser.add_argument("--amount", "--batch", type=int, default=4, nargs="?")
        parser.add_argument(
            "--nprompt", "--negative-prompt", type=str, default=None, nargs="*"
        )

        try:
            values = vars(parser.parse_args(argument.split(" ")))
        except Exception:
            raise BadArgument()

        if not values["prompt"]:
            raise BadArgument()

        values["prompt"] = " ".join(values["prompt"])

        if values["nprompt"]:
            values["nprompt"] = " ".join(values["nprompt"])

        if values["aspect"] not in MAGE_ASPECTS:
            values["aspect"] = process.extract(values["aspect"], MAGE_ASPECTS, limit=1)[
                0
            ][0]

        # Range: 25-150
        if not 25 <= values["steps"] <= 150:
            raise BadArgument("The steps argument must be between 25 and 150.")

        # Range: 0-30
        if not 0 <= values["guidance"] <= 30:
            raise BadArgument("The guidance argument must be between 0 and 30.")

        # Range: 1-9
        if not 1 <= values["amount"] <= 9:
            raise BadArgument("The amount argument must be between 1 and 9.")

        if values["seed"]:
            values["amount"] = 1

        return values


class StableDiffusionCommand(MixinMeta):
    async def _generate_stable_image(
        self, args: dict, bearer_token: str
    ) -> Optional[bytes]:
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 Edg/106.0.1370.42",
        }
        json = {
            "prompt": args["prompt"],
            "num_inference_steps": args["steps"],
            "guidance_scale": args["guidance"],
        }

        if args["aspect"] == "cinema":
            json["aspect_ratio"] = 1.7777777777777777
        elif args["aspect"] == "landscape":
            json["aspect_ratio"] = 1.5
        elif args["aspect"] == "square":
            json["aspect_ratio"] = 1.0
        elif args["aspect"] == "tablet":
            json["aspect_ratio"] = 0.6666666666666666
        elif args["aspect"] == "phone":
            json["aspect_ratio"] = 0.5625

        if args["nprompt"]:
            json["negative_prompt"] = args["nprompt"]

        if args["seed"]:
            json["seed"] = args["seed"]

        async with self.session.post(
            "https://api.mage.space/api/v2/images/generate", headers=headers, json=json, timeout=90
        ) as resp:
            if resp.status != 200:
                return
            data = await resp.json()
        url = data["results"][0]["image_url"]
        async with self.session.get(url) as resp:

            if resp.status != 200:
                return
            return await resp.read()

    @commands.command(aliases=["stable"])
    @commands.bot_has_permissions(embed_links=True)
    async def stablediffusion(self, ctx: Context, *, args: StableDiffusionArguments):
        """
        Generate art using Stable Diffusion.

        Arguments:
            `prompt:` The prompt to use for the image.
            `--aspect:` The aspect ratio to use for the image. Defaults to square. Options: cinema, landscape, square, tablet, phone.
            `--steps:` The number of inference steps to use. Defaults to 50. Range: 25-150.
            `--guidance:` The guidance scale to use. Defaults to 7.1. Range: 0-30.
            `--seed:` The seed to use for the image. Defaults to a random seed. If this is set, the amount argument will be ignored.
            `--amount:` The number of images to generate. Defaults to 4. Range: 1-9.
            `--nprompt:` The negative prompt to use for the image.
        """
        m = await ctx.reply("Generating art... This may take a while.")
        async with ctx.typing():
            bearer_token = await self._get_firebase_bearer_token(
                "AIzaSyAzUV2NNUOlLTL04jwmUw9oLhjteuv6Qr4"
            )
            if not bearer_token:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.reply("Failed to generate art. Please try again later.")
                return

            tasks = [
                self._generate_stable_image(args, bearer_token)
                for _ in range(args["amount"])
            ]
            images = await asyncio.gather(*tasks, return_exceptions=True)
            images = [i for i in images if isinstance(i, bytes)]
            if not images:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()

                await ctx.reply("Failed to generate art. Please try again later.")
                return

        await self.send_images(ctx, images)
