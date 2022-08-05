import contextlib
import datetime
import re
from typing import List
from urllib.parse import urlparse

import aiohttp
import discord
from discord.ext import tasks
from redbot.core import Config, commands, modlog
from redbot.core.bot import Red
from redbot.core.commands import Context

URL_REGEX_PATTERN = re.compile(
    r"^(?:http[s]?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.]+$"
)


class AntiPhishing(commands.Cog):
    """
    Protects users against phishing attacks.
    """

    __version__ = "1.2.12"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=73835)
        self.config.register_guild(action="ignore", caught=0)
        self.session = aiohttp.ClientSession()
        self.bot.loop.create_task(self.register_casetypes())
        self.bot.loop.create_task(self.get_phishing_domains())
        self.domains = []

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx: Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def register_casetypes(self) -> None:
        with contextlib.suppress(RuntimeError):
            # notify setting
            await modlog.register_casetype(
                name="phish_found",
                default_setting=True,
                image="🎣",
                case_str="Phishing Link Detected",
            )
            # delete setting
            await modlog.register_casetype(
                name="phish_deleted",
                default_setting=True,
                image="🎣",
                case_str="Phishing Link Detected - Auto-Deleted",
            )
            # kick setting
            await modlog.register_casetype(
                name="phish_kicked",
                default_setting=True,
                image="🎣",
                case_str="Phishing Link Detected - Auto-Kicked",
            )
            # ban setting
            await modlog.register_casetype(
                name="phish_banned",
                default_setting=True,
                image="🎣",
                case_str="Phishing Link Detected - Auto-Banned",
            )

    @tasks.loop(minutes=10)
    async def get_phishing_domains(self) -> None:
        domains = []

        headers = {
            "X-Identity": f"Red-DiscordBot, AntiPhishing v{self.__version__} (https://github.com/kaogurai/cogs)",
        }

        async with self.session.get("https://phish.sinking.yachts/v2/all", headers=headers) as request:
            if request.status == 200:
                data = await request.json()
                domains.extend(data)

        async with self.session.get(
            "https://bad-domains.walshy.dev/domains.json"
        ) as request:
            if request.status == 200:
                data = await request.json()
                domains.extend(data)

        deduped = list(set(domains))
        self.domains = deduped

    def extract_urls(self, message: str) -> List[str]:
        """
        Extract URLs from a message.
        """
        # Find all regex matches
        matches = URL_REGEX_PATTERN.findall(message)
        return matches

    def get_links(self, message: str) -> List[str]:
        """
        Get links from the message content.
        """
        # Remove zero-width spaces
        message = message.replace("\u200b", "")
        message = message.replace("\u200c", "")
        message = message.replace("\u200d", "")
        message = message.replace("\u2060", "")
        message = message.replace("\uFEFF", "")
        if message != "":
            links = self.extract_urls(message)
            if not links:
                return
            return list(set(links))

    async def handle_phishing(self, message: discord.Message, domain: str) -> None:
        domain = domain[:250]
        action = await self.config.guild(message.guild).action()
        if not action == "ignore":
            count = await self.config.guild(message.guild).caught()
            await self.config.guild(message.guild).caught.set(count + 1)
        if action == "notify":
            if message.channel.permissions_for(message.guild.me).send_messages:
                with contextlib.suppress(discord.NotFound):
                    embed = discord.Embed(
                        title="Warning",
                        description=f"{message.author.mention} has sent a phishing link.\n\nDo not click on the link.",
                        color=await self.bot.get_embed_color(message.guild),
                    )
                    embed.set_author(
                        name=message.author.display_name,
                        icon_url=message.author.avatar_url,
                    )
                    await message.reply(embed=embed)
                await modlog.create_case(
                    guild=message.guild,
                    bot=self.bot,
                    created_at=datetime.utcnow(),
                    action_type="phish_found",
                    user=message.author,
                    moderator=message.guild.me,
                    reason=f"Sent a phishing link: {domain}",
                )
        elif action == "delete":
            if message.channel.permissions_for(message.guild.me).manage_messages:
                with contextlib.suppress(discord.NotFound):
                    await message.delete()

                await modlog.create_case(
                    guild=message.guild,
                    bot=self.bot,
                    created_at=datetime.utcnow(),
                    action_type="phish_deleted",
                    user=message.author,
                    moderator=message.guild.me,
                    reason=f"Sent a phishing link: {domain}",
                )
        elif action == "kick":
            if (
                message.channel.permissions_for(message.guild.me).kick_members
                and message.channel.permissions_for(message.guild.me).manage_messages
            ):
                with contextlib.suppress(discord.NotFound):
                    await message.delete()
                    if (
                        message.author.top_role >= message.guild.me.top_role
                        or message.author == message.guild.owner
                    ):
                        return

                    await message.author.kick()

                await modlog.create_case(
                    guild=message.guild,
                    bot=self.bot,
                    created_at=datetime.utcnow(),
                    action_type="phish_kicked",
                    user=message.author,
                    moderator=message.guild.me,
                    reason=f"Sent a phishing link: {domain}",
                )
        elif action == "ban":
            if (
                message.channel.permissions_for(message.guild.me).ban_members
                and message.channel.permissions_for(message.guild.me).manage_messages
            ):
                with contextlib.suppress(discord.NotFound):
                    await message.delete()
                    if (
                        message.author.top_role >= message.guild.me.top_role
                        or message.author == message.guild.owner
                    ):
                        return

                    await message.author.ban()

                await modlog.create_case(
                    guild=message.guild,
                    bot=self.bot,
                    created_at=datetime.utcnow(),
                    action_type="phish_banned",
                    user=message.author,
                    moderator=message.guild.me,
                    reason=f"Sent a phishing link: {domain}",
                )

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        """
        Handles the logic for checking URLs.
        """

        if not message.guild or message.author.bot:
            return
        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return

        links = self.get_links(message.content)
        if not links:
            return

        for url in links:
            domain = urlparse(url).netloc
            if domain in self.domains:
                await self.handle_phishing(message, domain)
                return

    @commands.command(
        aliases=["checkforphish", "checkscam", "checkforscam", "checkphishing"]
    )
    @commands.bot_has_permissions(embed_links=True)
    async def checkphish(self, ctx: Context, url: str = None):
        """
        Check if a url is a phishing scam.

        You can either provide a url or reply to a message containing a url.
        """
        if not url and not ctx.message.reference:
            return await ctx.send_help()

        if not url:
            try:
                m = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            except discord.NotFound:
                await ctx.send_help()
                return
            url = m.content

        url = url.strip("<>")
        urls = self.extract_urls(url)
        if not urls:
            await ctx.send("That's not a valid URL.")
            return

        url = urls[0]
        status, redirects = await self.get_redirects(url)
        real_url = redirects[-1]
        domain = urlparse(real_url).netloc

        if domain in self.domains:
            await ctx.send(f"{real_url[:1000]} is a phishing scam.")
        else:
            await ctx.send(f"{real_url[:1000]} is likely not a phishing scam.")

    @commands.group(aliases=["antiphish"])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def antiphishing(self, ctx: Context):
        """
        Settings to set up the anti-phishing integration.
        """

    @antiphishing.command()
    async def action(self, ctx: Context, action: str):
        """
        Choose the action that occurs when a user sends a phishing scam.

        Options:
        `ignore` - Disables the anti-phishing integration (default)
        `notify` - Sends a message to the channel and says it's a phishing scam
        `delete` - Deletes the message
        `kick` - Kicks the author (also deletes the message)
        `ban` - Bans the author (also deletes the message)
        """
        if action not in ["ignore", "notify", "delete", "kick", "ban"]:
            await ctx.send(
                "That's not a valid action.\n\nOptions: `ignore`, `notify`, `delete`, `kick`, `ban`"
            )
            return

        await self.config.guild(ctx.guild).action.set(action)
        await ctx.send(f"Set the action to `{action}`.")

    @antiphishing.command()
    async def stats(self, ctx: Context):
        """
        Shows the current stats for the anti-phishing integration.
        """
        caught = await self.config.guild(ctx.guild).caught()
        s = "s" if caught != 1 else ""
        await ctx.send(f"I've caught `{caught}` phishing scam{s} in this server!")
