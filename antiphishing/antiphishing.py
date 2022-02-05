import contextlib
import re
from urllib.parse import urlparse

import aiohttp
import arrow
import discord
from redbot.core import Config, commands, modlog


class AntiPhishing(commands.Cog):
    """
    Protects users against phishing attacks.
    """

    __version__ = "1.1.1"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=73835)
        self.config.register_guild(action="ignore")
        self.session = aiohttp.ClientSession()
        self.bot.loop.create_task(self.register_casetypes())

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def register_casetypes(self):
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

    def extract_urls(self, message: str):
        """
        Extract URLs from a message.
        """
        return re.findall(
            r"(?:[A-z0-9](?:[A-z0-9-]{0,61}[A-z0-9])?\.)+[A-z0-9][A-z0-9-]{0,61}[A-z0-9]",
            message,
        )

    def make_message_for_api(self, message: str):
        """
        Make a message for the API.

        For privacy reasons, I don't want to send the real message, so we'll remove everything that isn't a URL.
        """
        # Remove zero-width spaces
        message = message.replace("\u200b", "")
        message = message.replace("\u200c", "")
        message = message.replace("\u200d", "")
        message = message.replace("\u2060", "")
        message = message.replace("\uFEFF", "")
        if message != "":
            urls = self.extract_urls(message)
            if not urls:
                return
            message = ""
            for url in urls:
                message += f"{url} "
            return message

    async def check_for_phishes(self, message: str):
        """
        Get information about a domain.
        """
        data = {
            "message": message,
        }
        headers = {
            "User-Agent": f"Red-DiscordBot/aiohttp/{aiohttp.__version__}/discord.py/{discord.__version__}/AntiPhishing/{self.__version__} (https://github.com/kaogurai/cogs/tree/master/antiphishing) | Bot ID: {self.bot.user.id}",
        }
        async with self.session.post(
            f"https://anti-fish.bitflow.dev/check", json=data, headers=headers
        ) as request:
            if request.status not in [
                200,
                404,
            ]:  # 404 is when the domain is not in the database
                return
            data = await request.json()
            return data

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        """
        Handles the logic for checking URLs.
        """

        if not message.guild or message.author.bot:
            return
        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return

        fake_message = self.make_message_for_api(message.content)
        if not fake_message:
            return

        data = await self.check_for_phishes(fake_message)
        if not data:
            return

        if data["match"]:
            action = await self.config.guild(message.guild).action()
            if action == "ignore":
                return
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
                        created_at=arrow.utcnow(),
                        action_type="phish_found",
                        user=message.author,
                        moderator=message.guild.me,
                        reason=f"Sent a phishing link: {data['matches'][0]['domain']}",
                    )
            if action == "delete":
                if message.channel.permissions_for(message.guild.me).manage_messages:
                    with contextlib.suppress(discord.NotFound):
                        await message.delete()

                    await modlog.create_case(
                        guild=message.guild,
                        bot=self.bot,
                        created_at=arrow.utcnow(),
                        action_type="phish_deleted",
                        user=message.author,
                        moderator=message.guild.me,
                        reason=f"Sent a phishing link: {data['matches'][0]['domain']}",
                    )

            if action == "kick":
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
                        created_at=arrow.utcnow(),
                        action_type="phish_kicked",
                        user=message.author,
                        moderator=message.guild.me,
                        reason=f"Sent a phishing link: {data['matches'][0]['domain']}",
                    )
            if action == "ban":
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
                        created_at=arrow.utcnow(),
                        action_type="phish_banned",
                        user=message.author,
                        moderator=message.guild.me,
                        reason=f"Sent a phishing link: {data['matches'][0]['domain']}",
                    )

    @commands.command(
        aliases=["checkforphish", "checkscam", "checkforscam", "checkphishing"]
    )
    @commands.bot_has_permissions(embed_links=True)
    async def checkphish(self, ctx, url: str):
        """
        Check if a url is a phishing scam.
        """
        url = url.strip("<>")
        urls = self.extract_urls(url)
        if not urls:
            await ctx.send("That's not a valid URL.")
            return

        url = urls[0]

        data = await self.check_for_phishes(url)
        if not data:
            await ctx.send("Something went wrong when looking up the URL.")
            return

        if data["match"]:
            if url.startswith("http") or url.startswith("https"):
                url = urlparse(url).netloc

            async with self.session.get(f"http://ip-api.com/json/{url}") as request:
                if request.status != 200:
                    await ctx.send("Be careful, that URL is a phishing scam.")
                    return

                ip_data = await request.json()
                if ip_data["status"] == "fail":
                    await ctx.send("Be careful, that URL is a phishing scam.")
                    return

            embed = discord.Embed(
                title="Warning",
                description=f"{url} is a phishing scam.\n\nDo not click on the link.",
                color=await self.bot.get_embed_color(ctx.guild),
            )
            embed.add_field(
                name="Country", value=f"{ip_data['country']} ({ip_data['countryCode']})"
            )
            embed.add_field(
                name="Region", value=f"{ip_data['regionName']} ({ip_data['region']})"
            )
            embed.add_field(name="City", value=f"{ip_data['city']}")
            embed.add_field(name="ISP", value=f"{ip_data['isp']}")
            embed.add_field(name="ASN", value=f"{ip_data['as']}")
            embed.add_field(name="Latitude", value=f"{ip_data['lat']}")
            embed.add_field(name="Longitude", value=f"{ip_data['lon']}")
            embed.add_field(name="IP Address", value=f"{ip_data['query']}")

        else:
            domain = urlparse(url).netloc

            async with self.session.get(f"http://ip-api.com/json/{domain}") as request:
                if request.status != 200:
                    await ctx.send("Be careful, that URL is a phishing scam.")
                    return

                ip_data = await request.json()

            if ip_data["status"] == "fail":
                await ctx.send("Be careful, that URL is a phishing scam.")
                return

            embed = discord.Embed(
                title="Safe",
                description=f"{url} is a not phishing scam.\n\nNo need to worry.",
                color=await self.bot.get_embed_color(ctx.guild),
            )
            embed.add_field(
                name="Country", value=f"{ip_data['country']} ({ip_data['countryCode']})"
            )
            embed.add_field(
                name="Region", value=f"{ip_data['regionName']} ({ip_data['region']})"
            )
            embed.add_field(name="City", value=f"{ip_data['city']}")
            embed.add_field(name="ISP", value=f"{ip_data['isp']}")
            embed.add_field(name="ASN", value=f"{ip_data['as']}")
            embed.add_field(name="Latitude", value=f"{ip_data['lat']}")
            embed.add_field(name="Longitude", value=f"{ip_data['lon']}")
            embed.add_field(name="IP Address", value=f"{ip_data['as']}")

        await ctx.send(embed=embed)

    @commands.group(aliases=["antiphish"])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def antiphishing(self, ctx):
        """
        Settings to set the anti-phishing integration.
        """

    @antiphishing.command()
    async def action(self, ctx, action: str):
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
