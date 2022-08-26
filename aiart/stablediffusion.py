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
from thefuzz import process

from .abc import MixinMeta
from .utils import NoExitParser

STABLE_DIFFUSION_ASPECTS = ["square", "widescreen", "portrait"]

# A lot of the code for parsing the arguments is inspired by flare's giveaways cog
# https://github.com/flaree/flare-cogs/blob/master/giveaways/converter.py


class StableDiffusionArguments(Converter):
    async def convert(self, ctx: Context, argument: str) -> dict:
        argument = argument.replace("—", "--")  # For iOS's weird smart punctuation

        parser = NoExitParser(add_help=False)
        parser.add_argument("prompt", type=str, nargs="*")
        parser.add_argument(
            "--aspect",
            "--aspect-ratio",
            type=str,
            default="square",
            nargs="?",
        )
        parser.add_argument("--image", type=str, default=None, nargs="?")
        parser.add_argument("--upscale", default=False, action="store_true")

        try:
            values = vars(parser.parse_args(argument.split(" ")))
        except Exception:
            raise BadArgument()

        if not values["prompt"]:
            raise BadArgument()

        values["prompt"] = " ".join(values["prompt"])

        if len(values["prompt"]) > 239:
            raise BadArgument("Prompt is too long. Please keep it under 240 characters.")

        if not values["image"] and ctx.message.attachments:
            values["image"] = ctx.message.attachments[0].url

        if values["aspect"] not in STABLE_DIFFUSION_ASPECTS:
            values["aspect"] = process.extract(
                values["aspect"], STABLE_DIFFUSION_ASPECTS, limit=1
            )[0][0]

        return values


class StableDiffusionCommand(MixinMeta):
    """
    Implements the Pixelz API for Stable Diffusion.
    """

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def stablediffusion(self, ctx: Context, *, args: StableDiffusionArguments):
        """
        Generate art using Stable Diffusion.

        You can use the following arguments (all optional):
        `--aspect <aspect>`: The aspect ratio of the art. Possible values are: `square`, `widescreen`, `portrait`. Default is `square`.

        `--image <image_url>`: The image URL to use for the art. If no image is provided, the first image attached to the message will be used.

        - `--upscale`: Upscale the images once requested. Keep in mind this means once you send the images you want, it will take a while to send the art. (normal is 512x512, upscale is 2048x2048)
        """
        m = await ctx.reply("Generating art... This may take a while.")
        async with ctx.typing():
            user_id = "".join(
                random.choice(string.ascii_letters + string.digits) for _ in range(28)
            )

            data = {
                "prompts": [
                    {
                        "prompt": args["prompt"],
                        "weight": 1,
                        "public": True,
                    }
                ],
                "public": True,
                "style": "stable",
                "user_id": user_id,
                "quality": "better",
                "aspect": args["aspect"],
            }

            if args["image"]:
                data["init_image"] = args["image"]
                data["init_image_prominence"] = 0.5

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
                    f"https://storage.googleapis.com/pixelz-images/{user_id}/{image_id}/preview.jpg",
                    headers=headers,
                ) as req:
                    if req.status == 200:
                        data = await req.read()
                        break

                await asyncio.sleep(15)

            with contextlib.suppress(discord.NotFound):
                await m.delete()

            embed = discord.Embed(
                title="Here's your art!",
                description="Type the number next to the image to select it. If you want more than one image, seperate the numbers with a comma.",
                color=await ctx.embed_color(),
            )
            embed.set_image(url="attachment://stablediffusion.jpg")
            file = discord.File(BytesIO(data), "stablediffusion.jpg")

            is_nsfw = await self.check_nsfw(data)
            if is_nsfw:
                with contextlib.suppress(discord.NotFound):
                    await m.delete()

                m = await ctx.reply(
                    "These images may contain NSFW content. Would you like me to DM you the image?"
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
                        await m.edit(content="Sending images...")
                    try:
                        await ctx.author.send(embed=embed, file=file)
                    except discord.Forbidden:
                        await ctx.reply(
                            "Failed to send images. Please make sure you have DMs enabled."
                        )
                        return
            else:
                await ctx.reply(embed=embed, file=file)

            def check(m):
                if is_nsfw:
                    return m.author == ctx.author and m.channel == ctx.author.dm_channel
                else:
                    return m.author == ctx.author and m.channel == ctx.channel

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=15)
            except asyncio.TimeoutError:
                return

            try:
                selected = [int(i) for i in msg.content.split(",")]
            except:
                return

            for i in selected:
                if i not in [1, 2, 3, 4, 5, 6]:
                    await ctx.reply("Invalid image number. Valid numbers are 1-6.")
                    return

            selected = [i - 1 for i in selected]

            for image in selected:
                if args["upscale"]:
                    data = {
                        "user_id": user_id,
                        "image_id": image_id,
                        "output_index": image,
                    }
                    async with self.session.post(
                        "https://api.pixelz.ai/upscale", json=data
                    ) as req:
                        if req.status != 200:
                            await ctx.reply(
                                "Failed to upscale image. Please try again later."
                            )
                            return

                        json = await req.json()
                        if json["success"] is False:
                            await ctx.reply(
                                "Failed to upscale image. Please try again later."
                            )
                            return

                        for x in range(12):
                            if x == 11:
                                await ctx.reply(
                                    "Failed to upscale image. Please try again later."
                                )
                                return

                            headers = {
                                "Referer": "https://pixelz.ai/",
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
                            }
                            async with self.session.get(
                                f"https://storage.googleapis.com/pixelz-images/{user_id}/{image_id}/hd-{image}.png",
                                headers=headers,
                            ) as req:
                                if req.status == 200:
                                    data = await req.read()
                                    break

                            await asyncio.sleep(15)

                else:
                    async with self.session.get(
                        f"https://storage.googleapis.com/pixelz-images/{user_id}/{image_id}/{image}.png"
                    ) as req:
                        if req.status != 200:
                            with contextlib.suppress(discord.NotFound):
                                await m.delete()
                            await ctx.reply(
                                "Failed to download art. Please try again later."
                            )
                            return
                        data = await req.read()

                buffer = BytesIO(data)

                if is_nsfw:
                    await ctx.author.send(
                        file=discord.File(buffer, "stablediffusion.png")
                    )
                else:
                    if selected[0] == image:
                        await ctx.reply(file=discord.File(buffer, "stablediffusion.png"))
                    else:
                        await ctx.send(file=discord.File(buffer, "stablediffusion.png"))
