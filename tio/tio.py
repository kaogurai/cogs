import io
import zlib
from typing import List, Tuple

import aiohttp
import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import escape, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from thefuzz import process


class Tio(commands.Cog):
    """
    A cog that interfaces with the tio.run website.
    """

    __version__ = "1.0.0"

    def __init__(self, bot: Red):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def cog_unload(self) -> None:
        self.bot.loop.create_task(self.session.close())

    def format_help_for_context(self, ctx: Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def red_delete_data_for_user(self, **kwargs):
        return

    async def get_languages(self) -> List[dict]:
        async with self.session.get("https://tio.run/languages.json") as req:
            if req.status != 200:
                return

            languages = await req.json()

        langs = []
        for l in languages:
            langs.append(
                {
                    "name": languages[l]["name"],
                    "value": l,
                    "link": languages[l].get("link", ""),
                }
            )

        return langs

    async def run_code(self, language: str, code: str) -> Tuple[List[str], List[str]]:
        payload = [
            {"command": "V", "payload": {"lang": [language.lower()]}},
            {"command": "F", "payload": {".code.tio": code}},
            {"command": "F", "payload": {".input.tio": ""}},
            {"command": "RC"},
        ]
        req = b""
        for instr in payload:
            req += instr["command"].encode()
            if "payload" in instr:
                [(name, value)] = instr["payload"].items()
                req += b"%s\0" % name.encode()
                if type(value) == str:
                    value = value.encode()
                req += b"%u\0" % len(value)
                if type(value) != bytes:
                    value = "\0".join(value).encode() + b"\0"
                req += value

        data = zlib.compress(req, 9)[2:-4]
        async with self.session.post(
            "https://tio.run/cgi-bin/static/b666d85ff48692ae95f24a66f7612256-run/93d25ed21c8d2bb5917e6217ac439d61",
            data=data,
        ) as req:
            if req.status != 200:
                return None, None
            data = await req.content.read()

        res = zlib.decompress(data, 31)
        weird_thing = res[:16]
        ret = res[16:].split(weird_thing)
        count = len(ret) >> 1
        output, debug = ret[:count], ret[count:]

        output = [r.decode("utf-8", "ignore") for r in output]
        debug = [e.decode("utf-8", "ignore") for e in debug]

        return output, debug

    def file_from_responses(self, output: str, debug: str) -> discord.File:
        result = f"""Output:\n{output}\n--------------------------------------------------\nDebug Info:\n{debug}"""
        f = io.BytesIO(result.encode("utf-8"))
        return discord.File(f, "output.txt")

    @commands.group(
        usage="<language> [line break or pipe] <code>",
        aliases=["run", "exec", "execute", "compile"],
        invoke_without_command=True,
    )
    async def code(self, ctx: Context, *, input: str) -> None:
        """
        Executes arbitrary code and returns the output.
        """
        try:
            lang, code = input.split("|", 1) if "|" in input else input.split("\n", 1)
        except ValueError:
            await ctx.send_help()
            return

        code = code.strip().strip("`")

        languages = await self.get_languages()
        if not languages:
            await ctx.send("Something went wrong with the API. Please try again later")
            return

        lang_names = [l["name"] for l in languages]
        match = process.extract(lang, lang_names, limit=1)

        for lang in languages:
            if lang["name"] == match[0][0]:
                lang = lang["value"]
                break

        output_list, debug_list = await self.run_code(lang, code)
        if not output_list or not debug_list:
            await ctx.send("Something went wrong with the API. Please try again later")
            return

        if output_list == [""]:
            output = "This code did not produce any output."
        else:
            output = "\n".join(output_list)

        debug = "\n".join(debug_list)

        for lang_obj in languages:
            if lang_obj["value"] == lang:
                lang = lang_obj
                break

        embed = discord.Embed(
            color=await ctx.embed_color(),
            title=f"{lang['name']} Output",
            url=lang["link"],
        )

        if (
            output.count("\n") > 35
            or debug.count("\n") > 35
            or len(output) > 1000
            or len(debug) > 1000
        ):
            embed.description = "The output is too long to display in an embed."
            await ctx.send(embed=embed, file=self.file_from_responses(output, debug))
        else:
            embed.add_field(
                name="Output",
                value=f"```{escape(output, formatting=True)}```",
                inline=False,
            )
            embed.add_field(
                name="Debug Info",
                value=f"```{escape(debug, formatting=True)}```",
                inline=False,
            )
            await ctx.send(embed=embed)

    @code.command(name="languages")
    async def code_languages(self, ctx: Context) -> None:
        """
        List all supported languages
        """
        languages = await self.get_languages()
        if not languages:
            await ctx.send("Something went wrong with the API. Please try again later")
            return

        text = ", ".join([f"[{l['name']}]({l['link']})" for l in languages])
        pages = [p for p in pagify(text=text, delims=",", page_length=4000)]
        embeds = []
        for i, page in enumerate(pages):
            embed = discord.Embed(
                color=await ctx.embed_color(),
                title="Supported Languages",
                description=page,
            )
            embed.set_footer(text=f"Page {i + 1}/{len(pages)}")
            embeds.append(embed)

        await menu(ctx, embeds, DEFAULT_CONTROLS)
