from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import humanize_list
import discord
import aiohttp


class AntiNSFW(commands.Cog):
    """Detects & Deletes NSFW Content."""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.config = Config.get_conf(self, identifier=69696969696969000)
        default_guild = {
            "enabled": False,
            "active_in_nsfw_channels": False,
            "filter_media": True,
            "filter_emotes": True,
            "filter_links": True,
            "requirement": 0.85,
            "deleted_message": "",
            "ignored_channels": [],
            "ignored_roles": [],
        }
        default_global = {"api": "http://localhost:5000/"}
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    @commands.group()
    @commands.mod()
    async def antinsfw(self, ctx):
        """Configures NSFW Detection"""
        pass

    @antinsfw.command()
    @commands.is_owner()
    async def api(self, ctx, url: str):
        """Changes the URL for the NSFW detection API"""
        await self.config.api.set(url)
        await ctx.tick()

    @antinsfw.command()
    @commands.bot_has_permissions(external_emojis=True)
    async def status(self, ctx):
        """Checks the current status of NSFW detection in the server"""
        embed = discord.Embed(title="Anti NSFW Status", colour=await ctx.embed_colour())
        requirement = (
            str(int(await self.config.guild(ctx.guild).requirement() * 100)) + "%"
        )
        if await self.config.guild(ctx.guild).enabled() is True:
            embed.add_field(
                name="Module Enabled",
                value="<:toggle_on:823619123438551070>",
                inline=False,
            )
        else:
            embed.add_field(
                name="Module Enabled",
                value="<:toggle_off:823619122872975364>",
                inline=False,
            )
        embed.add_field(name="Filter Requirement", value=requirement, inline=False)
        if await self.config.guild(ctx.guild).active_in_nsfw_channels() is True:
            if await self.config.guild(ctx.guild).enabled() is True:
                embed.add_field(
                    name="Filtering NSFW Channels",
                    value="<:toggle_on:823619123438551070>",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="Filtering NSFW Channels",
                    value="<:toggle_on:823619123438551070> (Module Disabled)",
                    inline=False,
                )
        else:
            embed.add_field(
                name="Filtering NSFW Channels",
                value="<:toggle_off:823619122872975364>",
                inline=False,
            )
        if await self.config.guild(ctx.guild).filter_media() is True:
            if await self.config.guild(ctx.guild).enabled() is True:
                embed.add_field(
                    name="Filtering Media",
                    value="<:toggle_on:823619123438551070>",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="Filtering Media",
                    value="<:toggle_on:823619123438551070> (Module Disabled)",
                    inline=False,
                )
        else:
            embed.add_field(
                name="Filtering Media",
                value="<:toggle_off:823619122872975364>",
                inline=False,
            )
        if await self.config.guild(ctx.guild).filter_emotes() is True:
            if await self.config.guild(ctx.guild).enabled() is True:
                embed.add_field(
                    name="Filtering Emotes",
                    value="<:toggle_on:823619123438551070>",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="Filtering Emotes",
                    value="<:toggle_on:823619123438551070> (Module Disabled)",
                    inline=False,
                )
        else:
            embed.add_field(
                name="Filtering Emotes",
                value="<:toggle_off:823619122872975364>",
                inline=False,
            )
        if await self.config.guild(ctx.guild).filter_links() is True:
            if await self.config.guild(ctx.guild).enabled() is True:
                embed.add_field(
                    name="Filtering Links",
                    value="<:toggle_on:823619123438551070>",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="Filtering Links",
                    value="<:toggle_on:823619123438551070> (Module Disabled)",
                    inline=False,
                )
        else:
            embed.add_field(
                name="Filtering Links",
                value="<:toggle_off:823619122872975364>",
                inline=False,
            )
        if await self.config.guild(ctx.guild).ignored_channels():
            ignored_channels = []
            for channel in await self.config.guild(ctx.guild).ignored_channels():
                format = "<#" + str(channel) + ">"
                ignored_channels.append(format)
            formatted_ignored_channels = humanize_list(ignored_channels)
            embed.add_field(
                name="Ignored Channels", value=formatted_ignored_channels, inline=False
            )
        if await self.config.guild(ctx.guild).ignored_roles():
            ignored_roles = []
            for role in await self.config.guild(ctx.guild).ignored_roles():
                format = "<@&" + str(role) + ">"
                ignored_roles.append(format)
            formatted_ignored_roles = humanize_list(ignored_roles)
            embed.add_field(
                name="Ignored Roles", value=formatted_ignored_roles, inline=False
            )
        await ctx.send(embed=embed)

    @antinsfw.command()
    async def toggle(self, ctx):
        """
        Toggles NSFW detection
        Check the `[p]antinsfw status` command to see your current status
        If it is enabled, it will disable it, and if it's enabled, it'll disable it
        """
        if await self.config.guild(ctx.guild).enabled() is True:
            await self.config.guild(ctx.guild).enabled.set(False)
            await ctx.tick()
        else:
            await self.config.guild(ctx.guild).enabled.set(True)
            await ctx.tick()

    @antinsfw.command()
    async def nsfwchannels(self, ctx):
        """
        Toggles the filtering of messages in NSFW channels
        If you only want some NSFW channels to be filtered, toggle this and use the `[p]antinsfw ignore channel add <channel>` command
        Check the `[p]antinsfw status` command to see your current status
        If it is enabled, it will disable it, and if it's enabled, it'll disable it
        """
        if await self.config.guild(ctx.guild).active_in_nsfw_channels() is True:
            await self.config.guild(ctx.guild).active_in_nsfw_channels.set(False)
            await ctx.tick()
        else:
            await self.config.guild(ctx.guild).active_in_nsfw_channels.set(True)
            await ctx.tick()

    @antinsfw.command()
    async def media(self, ctx):
        """
        Toggles the filtering of media
        Check the `[p]antinsfw status` command to see your current status
        If it is enabled, it will disable it, and if it's enabled, it'll disable it
        """
        if await self.config.guild(ctx.guild).filter_media() is True:
            await self.config.guild(ctx.guild).filter_media.set(False)
            await ctx.tick()
        else:
            await self.config.guild(ctx.guild).filter_media.set(True)
            await ctx.tick()

    @antinsfw.command()
    async def links(self, ctx):
        """
        Toggles the filtering of links
        Check the `[p]antinsfw status` command to see your current status
        If it is enabled, it will disable it, and if it's enabled, it'll disable it
        """
        if await self.config.guild(ctx.guild).filter_links() is True:
            await self.config.guild(ctx.guild).filter_links.set(False)
            await ctx.tick()
        else:
            await self.config.guild(ctx.guild).filter_links.set(True)
            await ctx.tick()

    @antinsfw.command()
    async def emotes(self, ctx):
        """
        Toggles the filtering of emotes
        Check the `[p]antinsfw status` command to see your current status
        If it is enabled, it will disable it, and if it's enabled, it'll disable it
        """
        if await self.config.guild(ctx.guild).filter_emotes() is True:
            await self.config.guild(ctx.guild).filter_emotes.set(False)
            await ctx.tick()
        else:
            await self.config.guild(ctx.guild).filter_emotes.set(True)
            await ctx.tick()

    @antinsfw.group()
    async def ignore(self, ctx):
        """Commands to ignore certain channels & roles"""
        pass

    @ignore.group()
    async def channel(self, ctx):
        """Ignore certain channels from the NSFW filter"""
        pass

    @channel.command(name="add")
    async def add_channel(self, ctx, channel: discord.TextChannel):
        """Adds a channel to be ignored by the NSFW filter"""
        channel_list = await self.config.guild(ctx.guild).ignored_channels()
        if channel.id not in channel_list:
            channel_list.append(channel.id)
            await self.config.guild(ctx.guild).ignored_channels.set(channel_list)
            await ctx.tick()
        else:
            await ctx.send("That channel is already being ignored.")

    @channel.command(name="remove")
    async def remove_channel(self, ctx, channel: discord.TextChannel):
        """Removes a channel from being ignored by the NSFW filter"""
        channel_list = await self.config.guild(ctx.guild).ignored_channels()
        if channel.id in channel_list:
            channel_list.remove(channel.id)
            await self.config.guild(ctx.guild).ignored_channels.set(channel_list)
            await ctx.tick()
        else:
            await ctx.send("That channel wasn't being ignored.")

    @channel.command(name="clear")
    async def clear_channel(self, ctx):
        """Clears all channels from being ignored by the NSFW filter"""
        channel_list = await self.config.guild(ctx.guild).ignored_channels()
        if not channel_list:
            await ctx.send("There's no channels to clear.")
        else:
            await self.config.guild(ctx.guild).ignored_channels.set([])
            await ctx.tick()

    @ignore.group()
    async def role(self, ctx):
        """Ignore certain roles from the NSFW filter"""
        pass

    @role.command(name="add")
    async def add_role(self, ctx, role: discord.Role):
        """Adds a role to be ignored by the NSFW filter"""
        role_list = await self.config.guild(ctx.guild).ignored_roles()
        if role.id not in role_list:
            role_list.append(role.id)
            await self.config.guild(ctx.guild).ignored_roles.set(role_list)
            await ctx.tick()
        else:
            await ctx.send("That role is already being ignored.")

    @role.command(name="remove")
    async def remove_role(self, ctx, role: discord.Role):
        """Removes a role from being ignored by the NSFW filter"""
        role_list = await self.config.guild(ctx.guild).ignored_roles()
        if role.id in role_list:
            role_list.remove(role.id)
            await self.config.guild(ctx.guild).ignored_roles.set(role_list)
            await ctx.tick()
        else:
            await ctx.send("That role is already being ignored.")

    @role.command(name="clear")
    async def clear_role(self, ctx):
        """Clears all roles from being ignored by the NSFW filter"""
        role_list = await self.config.guild(ctx.guild).ignored_roles()
        if not role_list:
            await ctx.send("There's no roles to clear.")
        else:
            await self.config.guild(ctx.guild).ignored_roles.set([])
            await ctx.tick()

    @antinsfw.command()
    async def requirement(self, ctx, requirement: int = 0.85):
        """
        Sets the requirement for the filter to be hit
        Not giving a number will reset it to 85%
        """
        if requirement > 100:
            await ctx.send("Please give a number from 0-100.")
            return
        if requirement < 0:
            await ctx.send("Please give a number from 0-100.")
            return
        else:
            better_requirement = requirement / 100
            await self.config.guild(ctx.guild).requirement.set(better_requirement)
            await ctx.tick()

    async def check_nsfw(self, link):
        api = await self.config.api()
        url = api + "?url=" + link
        async with self.session.get(url) as request:
            response = await request.json()
        if "score" in response:
            return response["score"]
        else:
            return "No Media"

    @commands.Cog.listener()  # for media filter
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return
        if not message.attachments:
            return
        if (
            await self.config.guild(message.guild).enabled() is True
            and await self.config.guild(message.guild).filter_media() is True
        ):
            req = await self.config.guild(message.guild).requirement()
            if len(message.attachments) == 1:
                attachment = message.attachments[0]
                score = await self.check_nsfw(attachment.url)
                # it wont always have a score
                if score > req:
                    try:
                        await message.delete()
                        if await self.config.guild(message.guild).deleted_message():
                            await message.channel.send(
                                await self.config.guild(message.guild).deleted_message()
                            )
                    except discord.errors.Forbidden:
                        await message.channel.send(
                            "I can't delete that, can you tell a admin to give me the Manage Messages permission?"
                        )
            else:
                await message.channel.send("Not the Multiple Attachments")
                # like actually do something for multiple attachments lol
