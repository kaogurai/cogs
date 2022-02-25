import urllib

import discord
from redbot.core import commands
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .abc import MixinMeta


class TextMixin(MixinMeta):
    @commands.command(aliases=["definition", "synonym", "antonym"])
    async def define(self, ctx, *, thing_to_define: str):
        """Define a word or phrase."""
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(thing_to_define)}"
        async with self.session.get(url) as resp:
            if resp.status == 404:
                await ctx.send("I couldn't find a definition for that.")
                return
            if resp.status != 200:
                await ctx.send("Something went wrong when trying to get the definition.")
                return
            data = await resp.json()
        embeds = []
        for i, result in enumerate(data):
            embed = discord.Embed(color=await ctx.embed_color())
            if "partOfSpeech" in result["meanings"][0]:
                embed.title = (
                    f"{result['word']} ({result['meanings'][0]['partOfSpeech']})"
                )
            else:
                embed.title = result["word"]
            embed.description = result["meanings"][0]["definitions"][0]["definition"]
            if "example" in result["meanings"][0]["definitions"][0]:
                embed.add_field(
                    name="Example",
                    value=result["meanings"][0]["definitions"][0]["example"],
                )
            if "synonyms" in result["meanings"][0]["definitions"][0]:
                embed.add_field(
                    name="Synonyms",
                    value=", ".join(result["meanings"][0]["definitions"][0]["synonyms"]),
                )
            if "antonyms" in result["meanings"][0]["definitions"][0]:
                embed.add_field(
                    name="Antonyms",
                    value=", ".join(result["meanings"][0]["definitions"][0]["antonyms"]),
                )
            if len(data) > 1:
                embed.set_footer(text=f"Result {i + 1}/{len(data)}")
            embeds.append(embed)
        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            await menu(ctx, embeds, DEFAULT_CONTROLS)
