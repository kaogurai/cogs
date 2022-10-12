import contextlib
from typing import List

import discord
from redbot.core import commands
from redbot.core.commands import Context
from redbot.core.commands import BadArgument, Context, Converter
from .utils import NoExitParser

from .abc import MixinMeta


class PlaygroundError(Exception):
    pass


class PlaygroundNSFWError(PlaygroundError):
    pass

class StableDiffusionArguments(Converter):
    async def convert(self, ctx: Context, argument: str) -> dict:
        argument = argument.replace("—", "--")  # For iOS's weird smart punctuation

        parser = NoExitParser(add_help=False)
        parser.add_argument("prompt", type=str, nargs="*")
        parser.add_argument("--width", type=int, default=512, nargs="?")
        parser.add_argument("--height", type=int, default=512, nargs="?")
        parser.add_argument("--prompt-guidance", type=int, default=7, nargs="?")
        parser.add_argument("--steps", type=int, default=25, nargs="?")
        parser.add_argument("--seed", type=int, default=None, nargs="?")


        try:
            values = vars(parser.parse_args(argument.split(" ")))
        except Exception:
            raise BadArgument()

        if not values["prompt"]:
            raise BadArgument()

        values["prompt"] = " ".join(values["prompt"])

        # Range: 256 - 1536, in increments of 64
        if values["width"] < 256 or values["width"] > 1536 or values["width"] % 64 != 0:
            raise BadArgument("Width must be between 256 and 1536, in increments of 64.")
        if values["height"] < 256 or values["height"] > 1536 or values["height"] % 64 != 0:
            raise BadArgument("Height must be between 256 and 1536, in increments of 64.")

        # Range: 0 - 30
        values["prompt-guidance"] = max(0, min(30, values["prompt_guidance"]))

        # Range: 10 - 150
        values["steps"] = max(10, min(150, values["steps"]))

        return values

class PlaygroundAI(MixinMeta):
    async def _generate_playground_images(self, model: str, params: dict) -> List[bytes]:
        json = {
            "modelType": model,
            "isPrivate": True,
            "num_images": 4,
        }
        json.update(params)
        cookies = {
            "__Secure-next-auth.session-token": "eca9ae53-49c6-47ba-a5c9-51b599ca2aa8"
        }
        async with self.session.post(
            "https://playgroundai.com/api/models",
            json=json,
            cookies=cookies,
        ) as req:
            if req.status == 200:
                json = await req.json()
            else:
                if "filter" in await req.text():
                    raise PlaygroundNSFWError
                raise PlaygroundError

        images = []
        for image in json["images"]:
            async with self.session.get(image["url"]) as req:
                if req.status == 200:
                    images.append(await req.read())

        if not images:
            raise PlaygroundError

        return images

    @commands.command(aliases=["dalle2", "d2"])
    @commands.bot_has_permissions(embed_links=True)
    async def dalle(self, ctx: Context, *, text: str):
        """
        Generate art using Dall-E 2.
        """
        m = await ctx.reply("Generating art... This may take a while.")
        async with ctx.typing():
            try:
                images = await self._generate_playground_images("dalle-2", {"prompt": text})
            except PlaygroundNSFWError:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.reply(
                    "Your prompt triggered the NSFW filters. Please try again with a different prompt."
                )
                return
            except PlaygroundError:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.reply("Failed to generate art. Please try again later.")
                return

        with contextlib.suppress(discord.NotFound):
            await m.delete()

        await self.send_images(ctx, images)

    @commands.command(aliases=["sd"])
    @commands.bot_has_permissions(embed_links=True)
    async def stablediffusion(self, ctx: Context, *, args: StableDiffusionArguments):
        """
        Generate art using Stable Diffusion.

        Arguments:
            prompt: The prompt to use.
            `--width:` The width of the image. Defaults to 512. Range: 256 - 1536, in increments of 64. (256, 320, 384, 448, 512, 576, 640, 704, 768, 832, 896, 960, 1024, 1088, 1152, 1216, 1280, 1344, 1408, 1472, 1536)
            `--height:` The height of the image. Defaults to 512. Range: 256 - 1536, in increments of 64. (see width)
            `--prompt-guidance:` The prompt guidance. Defaults to 7. Range: 0 - 30.
            `--steps:` The number of steps. Defaults to 25. Range: 10 - 150.
            `--seed:` The seed to use. Defaults to a random seed. If a seed is provided, only one image will be generated.
        """
        m = await ctx.reply("Generating art... This may take a while.")
        async with ctx.typing():
            params = {
                "prompt": args["prompt"],
                "width": args["width"],
                "height": args["height"],
                "cfg_scale": args["prompt-guidance"],
                "steps": args["steps"],
            }
            if args["seed"] is not None:
                params["seed"] = args["seed"]
                params["num_images"] = 1

            try:
                images = await self._generate_playground_images(
                    "stable-diffusion", params
                )
            except PlaygroundNSFWError:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.reply(
                    "Your prompt triggered the NSFW filters. Please try again with a different prompt."
                )
                return
            except PlaygroundError:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.reply("Failed to generate art. Please try again later.")
                return

        with contextlib.suppress(discord.NotFound):
            await m.delete()

        await self.send_images(ctx, images)
