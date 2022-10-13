import asyncio
import contextlib
import random
import string

import discord
from redbot.core import commands
from redbot.core.commands import BadArgument, Context, Converter
from thefuzz import process

from .abc import MixinMeta
from .utils import NoExitParser

PIXELZ_FILTERS = [
    "Oil Painting",
    "Watercolour",
    "Cosmic",
    "Fantasy",
    "Cyberpunk",
    "Cubist",
]
PIXELZ_ARTISTS = [
    "Van Gogh",
    "Salvador Dali",
    "Pablo Picasso",
    "Banksy",
    "Henri Matisse",
    "Michelangelo",
    "Andy Warhol",
    "Rembrandt",
    "Vermeer",
    "Jean-Antoine Watteau",
    "Eugene Delacroix",
    "Claude Monet",
    "Georges Seurat",
    "Edvard Munch",
    "Egon Schiele",
    "Gustav Klimt",
    "Rene Magritte",
    "Georgia O'Keeffe",
    "Edward Hopper",
    "Frida Kahlo",
    "Jackson Pollock",
    "Yayoi Kusama",
]
PIXELZ_ASPECTS = ["square", "landscape", "portrait"]
PIXELZ_ALGORITHMS = ["artistic", "portrait"]
PIXELZ_SYMMETRY = ["none", "vertical", "horizontal", "both"]

# A lot of the code for parsing the arguments is inspired by flare's giveaways cog
# https://github.com/flaree/flare-cogs/blob/master/giveaways/converter.py


class PixelzArguments(Converter):
    async def convert(self, ctx: Context, argument: str) -> dict:
        argument = argument.replace("—", "--")  # For iOS's weird smart punctuation

        parser = NoExitParser(add_help=False)
        parser.add_argument("prompt", type=str, nargs="*")
        parser.add_argument("--algorithm", type=str, default="artistic", nargs="?")
        parser.add_argument(
            "--aspect",
            "--aspect-ratio",
            type=str,
            default="square",
            nargs="?",
        )
        parser.add_argument("--filter", type=str, default=None, nargs="*")
        parser.add_argument("--artist", type=str, default=None, nargs="*")
        parser.add_argument("--symmetric", type=str, default="none", nargs="?")
        parser.add_argument("--image", type=str, default=None, nargs="?")

        try:
            values = vars(parser.parse_args(argument.split(" ")))
        except Exception:
            raise BadArgument()

        if not values["prompt"]:
            raise BadArgument()

        values["prompt"] = " ".join(values["prompt"])

        if len(values["prompt"]) > 239:
            raise BadArgument("Prompt is too long. Please keep it under 240 characters.")

        if values["artist"] and values["artist"] not in PIXELZ_ARTISTS:
            values["artist"] = process.extract(
                " ".join(values["artist"]), PIXELZ_ARTISTS, limit=1
            )[0][0]

        if values["filter"] and values["filter"] not in PIXELZ_FILTERS:
            values["filter"] = process.extract(
                " ".join(values["filter"]), PIXELZ_FILTERS, limit=1
            )[0][0]

        if values["algorithm"] not in PIXELZ_ALGORITHMS:
            values["algorithm"] = process.extract(
                values["algorithm"], PIXELZ_ALGORITHMS, limit=1
            )[0][0]

        if values["algorithm"] == "artistic":
            values["algorithm"] = "guided"
        else:
            values["algorithm"] = "guided_portrait"

        if values["symmetric"]:
            if values["symmetric"] not in PIXELZ_SYMMETRY:
                values["symmetric"] = process.extract(
                    values["symmetric"], PIXELZ_SYMMETRY, limit=1
                )[0][0]
        else:
            values["symmetric"] = "none"

        if not values["image"] and ctx.message.attachments:
            values["image"] = ctx.message.attachments[0].url

        if values["aspect"] not in PIXELZ_ASPECTS:
            values["aspect"] = process.extract(values["aspect"], PIXELZ_ASPECTS, limit=1)[
                0
            ][0]

        return values


class PixelzCommand(MixinMeta):
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def pixelz(self, ctx: Context, *, arguments: PixelzArguments):
        """
        Generate art using Pixelz.

        You can use the following arguments (all optional):
        `--algorithm <algorithm>`: The algorithm to use for the art. Possible values are: `artistic`, `portrait`. Default: `artistic`

        `--aspect <aspect>`: The aspect ratio of the art. Possible values are: `square`, `landscape`, `portrait`. Default is `square`.

        `--filter <filter>`: The filter to use for the art. Possible values are: `Oil Painting`, `Watercolour`, `Cosmic`, `Fantasy`, `Cyberpunk`, `Cubist`. Default is no filter.

        `--artist <artist>`: The artist to use for the art. Possible values are: `Van Gogh`, `Salvador Dali`, `Pablo Picasso`, `Banksy`, `Henri Matisse`, `Michelangelo`, `Andy Warhol`, `Rembrandt`, `Vermeer`, `Jean-Antoine Watteau`, `Eugene Delacroix`, `Claude Monet`, `Georges Seurat`, `Edvard Munch`, `Egon Schiele`, `Gustav Klimt`, `Rene Magritte`, `Georgia O'Keeffe`, `Edward Hopper`, `Frida Kahlo`, `Jackson Pollock`, `Yayoi Kusama`. Default is no artist.

        `--symmetric <symmetric>`: The symmetry of the art. Possible values are: `vertical`, `horizontal`, `both`. Default is `none`. Default is no symmetry.

        `--image <image_url>`: The image URL to use for the art. If no image is provided, the first image attached to the message will be used.
        """
        m = await ctx.reply("Generating art... This may take a while.")
        async with ctx.typing():
            user_id = "".join(
                random.choice(string.ascii_letters + string.digits) for _ in range(28)
            )

            data = {
                "prompts": [
                    {
                        "prompt": arguments["prompt"],
                        "weight": 1,
                        "public": True,
                    }
                ],
                "public": True,
                "style": arguments["algorithm"],
                "quality": "supreme",
                "user_id": user_id,
                "aspect": arguments["aspect"],
                "guided_symmetry": arguments["symmetric"],
            }

            if arguments["artist"]:
                data["artist"] = arguments["artist"]

            if arguments["filter"]:
                data["filter"] = arguments["filter"]

            if arguments["symmetric"]:
                data["guided_symmetry"] = "true"
            else:
                data["guided_symmetry"] = "none"

            if arguments["image"]:
                data["init_image"] = arguments["image"]
                data["init_image_prominence"] = "10"

            async with self.session.post(
                "https://api.pixelz.ai/preview", json=data
            ) as req:
                if req.status != 200:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
                    await ctx.reply("Failed to generate art. Please try again later.")
                    return
                json = await req.json()

            if json["success"] is False:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()
                await ctx.reply("Failed to generate art. Please try again later.")
                return

            image_id = json["process"]["generated_image_id"]

            for x in range(60):
                if x == 59:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
                    await ctx.reply("Failed to generate art. Please try again later.")
                    return

                headers = {
                    "Referer": "https://pixelz.ai/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
                }
                async with self.session.get(
                    f"https://storage.googleapis.com/pixelz-images/{user_id}/{image_id}/output_c.jpg",
                    headers=headers,
                ) as req:
                    if req.status == 200:
                        data = await req.read()
                        break

                await asyncio.sleep(15)

            with contextlib.suppress(discord.NotFound):
                await m.delete()

        await self.send_images(ctx, [data])
