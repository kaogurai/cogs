import contextlib
import random
from typing import List

import discord
from redbot.core import commands
from redbot.core.commands import BadArgument, Context, Converter
from thefuzz import process

from .abc import MixinMeta
from .utils import NoExitParser

PLAYGROUND_SESSIONS = ["eca9ae53-49c6-47ba-a5c9-51b599ca2aa8"]
DALLE_SIZES = ["small", "large"]


class PlaygroundError(Exception):
    pass


class PlaygroundNSFWError(PlaygroundError):
    pass


class DalleArguments(Converter):
    async def convert(self, ctx: Context, argument: str) -> dict:
        argument = argument.replace("—", "--")  # For iOS's weird smart punctuation

        parser = NoExitParser(add_help=False)
        parser.add_argument("prompt", type=str, nargs="*")
        parser.add_argument("--image", type=str, default=None, nargs="?")
        parser.add_argument("--size", type=str, default="large", nargs="?")

        try:
            values = vars(parser.parse_args(argument.split(" ")))
        except Exception:
            raise BadArgument()

        if not values["prompt"]:
            raise BadArgument()

        if not values["image"] and ctx.message.attachments:
            values["image"] = ctx.message.attachments[0].url

        values["size"] = process.extract(values["size"], DALLE_SIZES, limit=1)[0][0]

        values["prompt"] = " ".join(values["prompt"])

        return values


class DalleCommand(MixinMeta):
    async def _generate_playground_images(self, model: str, params: dict) -> List[bytes]:
        json = {
            "modelType": model,
            "isPrivate": True,
            "num_images": 4,
        }
        json.update(params)
        cookies = {"__Secure-next-auth.session-token": random.choice(PLAYGROUND_SESSIONS)}
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

    #@commands.command(aliases=["dalle2", "d2"])
    #@commands.bot_has_permissions(embed_links=True)
    async def dalle(self, ctx: Context, *, args: DalleArguments):
        """
        Generate art using Dall-E 2.

        Arguments:
            `prompt:` The prompt to use.
           ` --image:` The image to use as a prompt. Must be a URL. You can also upload an image as an attachment.
            `--size:` The size of the model to use. Can be `small` or `large`. Defaults to `large`.  `small` is 512x512, `large` is 1024x1024.
        """
        m = await ctx.reply("Generating art... This may take a while.")
        async with ctx.typing():
            try:
                if args["size"] == "small":
                    images = await self._generate_playground_images(
                        "dalle-2", {"prompt": args["prompt"], "width": 512, "height": 512}
                    )
                else:
                    images = await self._generate_playground_images(
                        "dalle-2",
                        {"prompt": args["prompt"], "width": 1024, "height": 1024},
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
