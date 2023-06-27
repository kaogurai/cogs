import contextlib
import json
import xml.etree.ElementTree as ET

import anthropic
import discord
from redbot.core import commands

from .abc import MixinMeta


class ClaudeMixin(MixinMeta):
    def _get_command_list(self) -> str:
        """
        Return a JSON representation of all commands and cogs in the bot.
        """
        cogs = []
        for cog in self.bot.cogs:
            cog_obj = self.bot.get_cog(cog)
            cog_data = {
                "name": cog,
                "description": cog_obj.__cog_group_description__,
                "commands": [],
            }
            for command in cog_obj.walk_commands():
                if command.hidden:
                    continue
                cog_data["commands"].append(
                    {
                        "name": command.name,
                        "description": command.help,
                        "params": [
                            {"name": param.name, "required": param.required}
                            for param in command.clean_params.values()
                        ],
                    }
                )
            cogs.append(cog_data)

        return json.dumps(cogs)

    async def get_response(self, user: discord.User, message: str) -> str:
        client = anthropic.Client(
            (await self.bot.get_shared_api_tokens("anthropic")).get("api_key")
        )

        prompt = f"{anthropic.HUMAN_PROMPT} You are an assistant providing information about a discord bot named '{self.bot.user.name}' who is talking to '{user.name}'. Use the data inside the <cogs></cogs> XML tags to help with your response.\n\n<cogs>{self._get_command_list()}</cogs>\n\nThis is the user's message: '{message}'\n\nPlease write your response to their message in <response></response> XML tags; if you have any doubt in your response, respond with you don't know.{anthropic.AI_PROMPT}"
        response = await client.acompletion(
            prompt=prompt,
            model="claude-instant-1-100k",
            max_tokens_to_sample=500,
        )
        root = ET.fromstring(response["completion"])
        return root.text

    @commands.Cog.listener("on_message_without_command")
    async def mention_response(self, message: discord.Message):
        if not await self.bot.allowed_by_whitelist_blacklist(who=message.author):
            return
        if message.author.bot:
            return
        if not message.guild:
            return
        if not message.channel.permissions_for(message.guild.me).send_messages:
            return
        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return
        if message.content.startswith(
            f"<@!{self.bot.user.id}> "
        ) or message.content.startswith(f"<@{self.bot.user.id}> "):
            msg = message.content.replace(f"<@!{self.bot.user.id}> ", "").replace(
                f"<@{self.bot.user.id}> ", ""
            )

            async with message.channel.typing():
                response = await self.get_response(message.author, msg)

            if response:
                with contextlib.suppress(discord.NotFound):
                    await message.reply(
                        response, allowed_mentions=discord.AllowedMentions.none()
                    )
