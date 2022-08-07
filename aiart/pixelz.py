import argparse
import asyncio
import contextlib
import random
import string
from io import BytesIO

import discord
from redbot.core import commands
from redbot.core.commands import BadArgument, Context, Converter
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

from .abc import MixinMeta

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
PIXELZ_QUALITIES = ["normal", "better", "best", "supreme"]
PIXELZ_ASPECTS = ["square", "landscape", "portrait"]
PIXELZ_ALGORITHMS = ["artistic", "portrait"]
PIXELZ_SYMMETRY = ["none", "vertical", "horizontal", "both"]

# A lot of the code for parsing the arguments is taken from flare's giveaways cog
# https://github.com/flaree/flare-cogs/blob/master/giveaways/converter.py


class NoExitParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise BadArgument()


class PixelzArguments(Converter):
    def get_parser(self) -> NoExitParser:
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
        parser.add_argument("--quality", type=str, default="normal", nargs="?")
        return parser

    async def convert(self, ctx: Context, argument: str) -> dict:
        argument = argument.replace("—", "--")  # For iOS's weird smart punctuation

        parser = self.get_parser()

        try:
            values = vars(parser.parse_args(argument.split(" ")))
        except Exception:
            raise BadArgument(self.get_help_text())

        if not values["prompt"]:
            raise BadArgument()

        values["prompt"] = " ".join(values["prompt"])

        if len(values["prompt"]) > 239:
            raise BadArgument("Prompt is too long. Please keep it under 240 characters.")

        if values["artist"]:
            values["artist"] = " ".join(values["artist"])

            if values["artist"] not in PIXELZ_ARTISTS:
                raise BadArgument(
                    "Artist not found. Please use one of the following: "
                    + ", ".join(PIXELZ_ARTISTS)
                )

        if values["filter"]:
            values["filter"] = " ".join(values["filter"])

            if values["filter"] not in PIXELZ_FILTERS:
                raise BadArgument(
                    "Filter not found. Please use one of the following: "
                    + ", ".join(PIXELZ_FILTERS)
                )

        if values["quality"] not in PIXELZ_QUALITIES:
            raise BadArgument(
                "Quality not found. Please use one of the following: "
                + ", ".join(PIXELZ_QUALITIES)
            )

        if values["algorithm"] not in PIXELZ_ALGORITHMS:
            raise BadArgument(
                "Algorithm not found. Please use one of the following: "
                + ", ".join(PIXELZ_ALGORITHMS)
            )

        if values["algorithm"] == "artistic":
            values["algorithm"] = "guided"
        else:
            values["algorithm"] = "guided_portrait"

        if values["symmetric"]:
            if values["symmetric"] not in PIXELZ_SYMMETRY:
                raise BadArgument(
                    "Symmetric not found. Please use one of the following: "
                    + ", ".join(PIXELZ_SYMMETRY)
                )
        else:
            values["symmetric"] = "none"

        return values


class PixelzCommand(MixinMeta):
    """
    Implements the Internal Pixelz API used in their web client.
    """

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def pixelz(self, ctx: Context, *, arguments: PixelzArguments):
        """
        Generate art using Pixelz.

        You can use the following arguments:
        `--algorithm <algorithm>`: The algorithm to use for the art. Possible values are: `artistic`, `portrait`. Default: `artistic`

        `--aspect <aspect>`: The aspect ratio of the art. Possible values are: `square`, `landscape`, `portrait`. Default is `square`.

        `--filter <filter>`: The filter to use for the art. Possible values are: `Oil Painting`, `Watercolour`, `Cosmic`, `Fantasy`, `Cyberpunk`, `Cubist`. Default is no filter.

        `--artist <artist>`: The artist to use for the art. Possible values are: `Van Gogh`, `Salvador Dali`, `Pablo Picasso`, `Banksy`, `Henri Matisse`, `Michelangelo`, `Andy Warhol`, `Rembrandt`, `Vermeer`, `Jean-Antoine Watteau`, `Eugene Delacroix`, `Claude Monet`, `Georges Seurat`, `Edvard Munch`, `Egon Schiele`, `Gustav Klimt`, `Rene Magritte`, `Georgia O'Keeffe`, `Edward Hopper`, `Frida Kahlo`, `Jackson Pollock`, `Yayoi Kusama`. Default is no artist.

        `--symmetric <symmetric>`: The symmetry of the art. Possible values are: `vertical`, `horizontal`, `both`. Default is `none`. Default is no symmetry.

        `--quality <quality>`: The quality of the art. Possible values are: `normal`, `better`, `best`, `supreme`. Default is `normal`.
        """

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
                "quality": arguments["quality"],
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

            async with self.session.post(
                "https://api.pixelz.ai/preview", json=data
            ) as req:
                if req.status != 200:
                    await ctx.send("Failed to generate art. Please try again later.")
                    return
                json = await req.json()

            if json["success"] is False:
                await ctx.send("Failed to generate art. Please try again later.")
                return

            image_id = json["process"]["generated_image_id"]

            for x in range(60):
                if x == 59:
                    await ctx.send("Failed to generate art. Please try again later.")
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

            embed = discord.Embed(
                title="Here's your art!",
                color=await ctx.embed_color(),
            )
            embed.set_image(url="attachment://pixelz.jpg")
            file = discord.File(BytesIO(data), "pixelz.jpg")

            is_nsfw = await self.check_nsfw(data)
            if is_nsfw:

                m = await ctx.send(
                    f"{ctx.author.mention}, this image may contain NSFW content. Would you like me to DM you the image?"
                )
                start_adding_reactions(m, ReactionPredicate.YES_OR_NO_EMOJIS)
                pred = ReactionPredicate.yes_or_no(m, ctx.author)
                try:
                    await ctx.bot.wait_for("reaction_add", check=pred, timeout=60)
                except asyncio.TimeoutError:
                    with contextlib.suppress(discord.NotFound):
                        await m.delete()
                    return
                if pred.result is True:
                    with contextlib.suppress(discord.NotFound):
                        await m.edit(content=f"{ctx.author.mention}, sending image...")
                    try:
                        await ctx.author.send(embed=embed, file=file)
                    except discord.Forbidden:
                        await ctx.send(
                            "Failed to send image. Please make sure you have DMs enabled."
                        )
                    return
            else:
                await ctx.send(embed=embed, file=file, content=ctx.author.mention)
