import contextlib
import re
from urllib.parse import quote, urlparse

import aiohttp
import arrow
import discord
import redbot
from discord.ext import tasks
from redbot.core import Config, commands, modlog


class AntiPhishing(commands.Cog):
    """
    Protects users against phishing attacks.
    """

    __version__ = "1.2.6"

    def __init__(self, bot):
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

    @tasks.loop(minutes=10)
    async def get_phishing_domains(self):
        domains = []

        async with self.session.get(
            "https://api.hyperphish.com/gimme-domains"
        ) as request:
            if request.status == 200:
                data = await request.json()
                domains.extend(data)

        async with self.session.get("https://phish.sinking.yachts/v2/all") as request:
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

    def extract_urls(self, message: str):
        """
        Extract URLs from a message.
        """
        return re.findall(
            r"(?:[A-z0-9](?:[A-z0-9-]{0,61}[A-z0-9])?\.)+[A-z0-9][A-z0-9-]{0,61}[A-z0-9]",
            message,
        )

    def get_links(self, message: str):
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

    async def get_redirects(self, url: str):
        """
        Get the real URL of a URL.
        """
        if not url.startswith("http://") or not url.startswith("https://"):
            url = f"https://{url}"
        data = {
            "method": "G",
            "redirection": "true",
            "url": url,
            "locationid": "25",
            "headername": "User-Agent",
            "headervalue": f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.80 Safari/537.36 Red-DiscordBot/{redbot.__version__} aiohttp/{aiohttp.__version__} discord.py/{discord.__version__} AntiPhishing/{self.__version__}",
        }
        # I am very well aware that you could just use aiohttp to do this
        # But, this way it's not sending requests from the bot's IP, since I don't want users to need to set up a proxy server
        async with self.session.post(
            "https://www.site24x7.com/tools/restapi-tester", data=data
        ) as request:
            if request.status != 200:
                return None, [
                    url
                ]  # If we can't get the real URL, just return the original one
            data = await request.json()
            if "responsecode" in data and "rurls" in data:
                return data["responsecode"], data["rurls"]
            return None, [url]

    async def handle_phishing(self, message, domain):
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
                    created_at=arrow.utcnow(),
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
                    created_at=arrow.utcnow(),
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
                    created_at=arrow.utcnow(),
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
                    created_at=arrow.utcnow(),
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

        domains = []

        for link in links:
            _, redirects = await self.get_redirects(link)
            link = redirects[-1]
            domains.append(link)

        for domain in domains:
            domain = urlparse(domain).netloc
            if domain in self.domains:
                await self.handle_phishing(message, domain)
                return

    @commands.command(
        aliases=["checkforphish", "checkscam", "checkforscam", "checkphishing"]
    )
    @commands.bot_has_permissions(embed_links=True)
    async def checkphish(self, ctx, url: str = None):
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
            async with self.session.get(
                f"http://ip-api.com/json/{quote(domain)}"
            ) as request:
                if request.status != 200:
                    await ctx.send("Be careful, that URL is a phishing scam.")
                    return

                ip_data = await request.json()
                if ip_data["status"] == "fail":
                    await ctx.send("Be careful, that URL is a phishing scam.")
                    return

            embed = discord.Embed(
                title="Warning",
                description=f"That URL is a phishing scam.\n\nDo not click on the link.",
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
            if status:
                embed.add_field(name="Status Code", value=f"{status}")

            if len(redirects) > 1:
                redirects_msg = ""
                for x, redirect in enumerate(redirects):
                    redirects_msg += f"{x+1}. {redirect}\n"
                embed.add_field(
                    name="Redirects", value=redirects_msg[:1000], inline=False
                )

        else:

            async with self.session.get(
                f"http://ip-api.com/json/{quote(domain)}"
            ) as request:
                if request.status != 200:
                    await ctx.send("No need to worry, that URL is not a phishing scam.")
                    return

                ip_data = await request.json()

                if ip_data["status"] == "fail":
                    await ctx.send("No need to worry, that URL is not a phishing scam.")
                    return

            embed = discord.Embed(
                title="URL Safe",
                description=f"That URL is a not phishing scam.",
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
            if status:
                embed.add_field(name="Status Code", value=f"{status}")
            if len(redirects) > 1:
                redirects_msg = ""
                for x, redirect in enumerate(redirects):
                    redirects_msg += f"{x+1}. {redirect}\n"
                embed.add_field(
                    name="Redirects", value=redirects_msg[:1000], inline=False
                )

        await ctx.send(embed=embed)

    @commands.group(aliases=["antiphish"])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def antiphishing(self, ctx):
        """
        Settings to set up the anti-phishing integration.
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

    @antiphishing.command()
    async def stats(self, ctx):
        """
        Shows the current stats for the anti-phishing integration.
        """
        caught = await self.config.guild(ctx.guild).caught()
        s = "s" if caught != 1 else ""
        await ctx.send(f"I've caught `{caught}` phishing scam{s} in this server!")
