import asyncio
import base64
import contextlib
import re

import discord
from redbot.core import commands
from redbot.core.commands import BadArgument, Context, Converter

from .abc import MixinMeta
from .utils import NoExitParser


class NemuSonaConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> int:
        argument = argument.replace("—", "--")  # For iOS's weird smart punctuation

        parser = NoExitParser(add_help=False)
        parser.add_argument("prompt", type=str, nargs="*")
        parser.add_argument(
            "-n", "--negative", "--negative-prompt", type=str, default=[""], nargs="*"
        )
        parser.add_argument("--cfg-scale", type=int, default=10)
        parser.add_argument("--denoising-strength", type=float, default=0.5)
        parser.add_argument("--seed", type=int, default=-1)

        try:
            values = vars(parser.parse_args(argument.split(" ")))
        except Exception:
            raise BadArgument()

        if not values["prompt"]:
            raise BadArgument()

        values["prompt"] = " ".join(values["prompt"])
        values["negative"] = " ".join(values["negative"])

        # cfg_scale is a number between 1 and 20, inclusive
        if not 1 <= values["cfg_scale"] <= 20:
            raise BadArgument()

        # denoising_strength is a number between 0 and 1, inclusive
        if not 0 <= values["denoising_strength"] <= 1:
            raise BadArgument()

        if values["seed"] < -1:
            raise BadArgument()

        return values


class NemuSonaCommands(MixinMeta):
    async def _generate_nemusona_images(
        self, ctx: Context, model: str, args: NemuSonaConverter
    ) -> None:
        m = await ctx.reply("Generating art... This may take a while.")
        async with ctx.typing():
            r = re.compile(r"https://danbooru.donmai.us/posts/(\d+)")
            matches = r.findall(args["prompt"])
            if matches:
                async with self.session.get(
                    f"https://danbooru.donmai.us/posts/{matches[0]}.json"
                ) as resp:
                    if resp.status == 200:
                        j = await resp.json()
                        args["prompt"] = j["tag_string"]
                    else:
                        await ctx.send("Something went wrong when extracting tags.")
                        return

            data = {
                "prompt": args["prompt"],
                "negative_prompt": args["negative"],
                "cfg_scale": args["cfg_scale"],
                "denoising_strength": args["denoising_strength"],
                "seed": args["seed"],
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36",
            }
            async with self.session.post(
                f"https://waifus-api.nemusona.com/job/submit/{model}",
                json=data,
                headers=headers,
            ) as r:
                if r.status == 429:
                    await ctx.send("Hit the rate limit. Please try again later.")
                    return
                elif r.status != 201:
                    await ctx.send("Something went wrong. Please try again later.")
                    return

                id = await r.text()

            for x in range(300):
                async with self.session.get(
                    f"https://waifus-api.nemusona.com/job/status/{model}/{id}",
                    headers=headers,
                ) as r:
                    if r.status == 429:
                        await ctx.send("Hit the rate limit. Please try again later.")
                        return
                    elif r.status != 200:
                        await ctx.send("Something went wrong. Please try again later.")
                        return

                    status = await r.text()

                    if status == "failed":
                        with contextlib.suppress(discord.NotFound):
                            await m.delete()
                        await ctx.send("Something went wrong. Please try again later.")
                        return
                    elif status == "completed":
                        break

                    if x == 299:
                        with contextlib.suppress(discord.NotFound):
                            await m.delete()
                        await ctx.send("Timed out. Please try again later.")
                        return

                    await asyncio.sleep(1)

            async with self.session.get(
                f"https://waifus-api.nemusona.com/job/result/{model}/{id}",
                headers=headers,
            ) as r:
                if r.status == 429:
                    await ctx.send("Hit the rate limit. Please try again later.")
                    return
                elif r.status != 200:
                    await ctx.send("Something went wrong. Please try again later.")
                    return

                j = await r.json()
                image = base64.b64decode(j["base64"])

        await self.send_images(ctx, [image], f"Seed: {j['seed']}")

    @commands.command()
    async def anything(self, ctx: Context, *, args: NemuSonaConverter):
        """
        Generate art using the Anything v4.5 model.

        Warning: This model has a high likelihood of generating NSFW content (it will still be behind the NSFW filter.)

        **Arguments:**
            `prompt`: The prompt to use for the art.
            `--negative`: The negative prompt to use for the model.
            `--cfg-scale`: The cfg scale to use for the model. This is a number between 1 and 10, inclusive.
            `--denoising-strength`: The denoising strength to use for the model. This is a number between 0 and 1, inclusive.
        """
        await self._generate_nemusona_images(ctx, "anything", args)

    @commands.command()
    async def aom(self, ctx: Context, *, args: NemuSonaConverter):
        """
        Generate art using the AOM3 model.

        Warning: This model has a high likelihood of generating NSFW content (it will still be behind the NSFW filter.)

        **Arguments:**
            `prompt`: The prompt to use for the art.
            `--negative`: The negative prompt to use for the model.
            `--cfg-scale`: The cfg scale to use for the model. This is a number between 1 and 10, inclusive.
            `--denoising-strength`: The denoising strength to use for the model. This is a number between 0 and 1, inclusive.
        """
        await self._generate_nemusona_images(ctx, "aom", args)

    @commands.command()
    async def counterfeit(self, ctx: Context, *, args: NemuSonaConverter):
        """
        Generate art using the Counterfeit v2.5 model.

        Warning: This model has a high likelihood of generating NSFW content (it will still be behind the NSFW filter.)

        **Arguments:**
            `prompt`: The prompt to use for the art.
            `--negative`: The negative prompt to use for the model.
            `--cfg-scale`: The cfg scale to use for the model. This is a number between 1 and 10, inclusive.
            `--denoising-strength`: The denoising strength to use for the model. This is a number between 0 and 1, inclusive.
        """
        await self._generate_nemusona_images(ctx, "counterfeit", args)
