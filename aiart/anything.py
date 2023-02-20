import contextlib

import discord
import base64
from redbot.core import commands
from redbot.core.commands import BadArgument, Context, Converter

from .abc import MixinMeta
from .utils import NoExitParser


class AnythingConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> int:
        argument = argument.replace("—", "--")  # For iOS's weird smart punctuation

        parser = NoExitParser(add_help=False)
        parser.add_argument("prompt", type=str, nargs="*")
        parser.add_argument(
            "-n", "--negative", "--negative-prompt", type=str, default=[""], nargs="*"
        )
        parser.add_argument("--cfg-scale", type=int, default=10)
        parser.add_argument("--denoising-strength", type=float, default=1.0)

        try:
            values = vars(parser.parse_args(argument.split(" ")))
        except Exception:
            raise BadArgument()

        if not values["prompt"]:
            raise BadArgument()

        values["prompt"] = " ".join(values["prompt"])
        values["negative"] = " ".join(values["negative"])

        # cfg_scale is a number between 1 and 10, inclusive
        if not 1 <= values["cfg_scale"] <= 10:
            raise BadArgument()

        # denoising_strength is a number between 0 and 1, inclusive
        if not 0 <= values["denoising_strength"] <= 1:
            raise BadArgument()

        return values


class AnythingCommand(MixinMeta):
    @commands.command()
    async def anything(self, ctx: Context, *, args: AnythingConverter):
        """
        Generate art using the Anything V4 model.

        Warning: This model has a high likelihood of generating NSFW content (it will still be behind the NSFW filter.)

        Arguments:
            `prompt`: The prompt to use for the model.
            `--negative`: The negative prompt to use for the model.
            `--cfg-scale`: The cfg scale to use for the model. This is a number between 1 and 10, inclusive.
            `--denoising-strength`: The denoising strength to use for the model. This is a number between 0 and 1, inclusive.
        """
        m = await ctx.reply("Generating art... This may take a while.")
        async with ctx.typing():
            data = {
                "prompt": args["prompt"],
                "negative_prompt": args["negative"],
                "cfg_scale": args["cfg_scale"],
                "denoising_strength": args["denoising_strength"],
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36",
            }
            async with self.session.post(
                "https://waifus-api.nemusona.com/generate",
                json=data,
                headers=headers,
            ) as r:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()

                if r.status == 429:
                    await ctx.send("Hit the rate limit. Please try again later.")
                    return
                elif r.status != 200:
                    await ctx.send("Something went wrong. Please try again later.")
                    return

                image = base64.b64decode(await r.text())

        await self.send_images(ctx, [image])
