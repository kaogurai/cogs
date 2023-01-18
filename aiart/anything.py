import contextlib

import discord
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

        try:
            values = vars(parser.parse_args(argument.split(" ")))
        except Exception:
            raise BadArgument()

        if not values["prompt"]:
            raise BadArgument()

        values["prompt"] = " ".join(values["prompt"])
        values["negative"] = " ".join(values["negative"])

        return values


class AnythingCommand(MixinMeta):
    @commands.command()
    async def anything(self, ctx: Context, *, args: AnythingConverter):
        """
        Generate art using the Anything V4 model.

        Arguments:
            `prompt`: The prompt to use for the model.
            `--negative`: The negative prompt to use for the model.
        """
        m = await ctx.reply("Generating art... This may take a while.")
        async with ctx.typing():
            data = {
                "prompt": args["prompt"],
                "negative_prompt": args["negative"],
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36",
            }
            async with self.session.post(
                "https://waifus-api.nemusona.com/api/generate",
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

                image = await r.read()

        await self.send_images(ctx, [image])
