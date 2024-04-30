import contextlib

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu


class GuildManager(commands.Cog):
    """
    Manages the servers your bot is in.
    """

    __version__ = "2.1.0"

    def __init__(self, bot: Red):
        """
        This initializes the cog by setting up the datastore
        and ensuring that the bot has not been invited to any
        servers that are not whitelisted while offline.
        """
        self.bot = bot
        self.config = Config.get_conf(self, identifier=567856)
        default_global = {
            "whitelist": [],
            "toggle": False,
        }
        self.config.register_global(**default_global)
        self.bot.loop.create_task(self.ensure_requirements())

    async def red_delete_data_for_user(self, **kwargs):
        """
        This cog does not store user data.
        """
        return

    def format_help_for_context(self, ctx: Context) -> str:
        """
        Displays the cog version in the help menu.
        """
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def leave(self, guild: discord.Guild) -> None:
        """
        Leaves a guild and sends a message to the system channel if possible.
        """
        if (
            hasattr(guild, "system_channel")
            and guild.system_channel
            and guild.system_channel.permissions_for(guild.me).send_messages
        ):
            with contextlib.suppress(discord.Forbidden):
                m = (
                    "I'm leaving this server.\n\n"
                    "I am a private bot and you haven't been approved to use me."
                )
                embed = discord.Embed(
                    title="Hey there!",
                    color=await self.bot.get_embed_colour(guild.system_channel),
                    description=m,
                )
                await guild.system_channel.send(embed=embed)

        await guild.leave()

    async def ensure_requirements(self) -> None:
        """
        Leaves any guilds that are not whitelisted
        """
        toggle = await self.config.toggle()
        if not toggle:
            return

        for guild in self.bot.guilds:
            # Skips guilds not loaded yet
            if not guild:
                continue

            if guild.id in await self.config.whitelist():
                continue

            await self.leave(guild)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """
        Leaves newly joined guild if not whitelisted.
        """
        # Skip guild if not loaded yet
        if not guild:
            return

        # Skip guild if it is in whitelist
        if guild.id in await self.config.whitelist():
            return

        await self.leave(guild)

    @commands.is_owner()
    @commands.group(aliases=["guildmgr"])
    async def guildmanager(self, ctx: Context):
        """
        Manage bot guilds.
        """

    @guildmanager.command(name="toggle")
    async def guildmanager_toggle(self, ctx: Context):
        """
        Toggle the guild manager.
        """
        toggle = await self.config.toggle()
        if toggle:
            await ctx.send("The guild manager is now disabled.")
        else:
            await ctx.send(
                f"The guild manager is now enabled. I will leave any servers that aren't whitelisted on cog load, cog unload, and the invokation of the `{ctx.clean_prefix}guildmanager whitelist` command. Please either disable the guild manager or whitelist the servers you want to use the bot in now."
            )

        await self.config.toggle.set(not toggle)

    @guildmanager.command(name="enforce")
    async def guildmanager_enforce(self, ctx: Context):
        """
        Enforce guild requirements.
        """
        await self.ensure_requirements()
        await ctx.tick()

    @guildmanager.command(name="add")
    async def guildmanager_add(self, ctx: Context, id: int):
        """
        Add a guild to the whitelist.

        Arguments:
        `id`: The ID of the guild to be added.
        """
        whitelist = await self.config.whitelist()

        if id in whitelist:
            await ctx.send("This guild is already in the whitelist.")
            return
        else:
            whitelist.append(id)
            await self.config.whitelist.set(whitelist)
            await ctx.send(f"Added `{id}` to the whitelist.")

    @guildmanager.command(name="addall")
    async def guildmanager_addall(self, ctx: Context):
        """
        Add all guilds the bot is currently in to the whitelist.
        """
        whitelist = await self.config.whitelist()
        for guild in self.bot.guilds:
            if guild.id not in whitelist:
                whitelist.append(guild.id)
        await self.config.whitelist.set(whitelist)
        await ctx.send("Added all guilds to the whitelist.")

    @guildmanager.command(name="remove")
    async def guildmanager_remove(self, ctx: Context, id: int):
        """
        Remove a guild from the whitelist.

        Arguments:
        `id`: The ID of the guild to be removed.
        """
        whitelist = await self.config.whitelist()

        if id not in whitelist:
            await ctx.send("This guild is not in the whitelist.")
            return
        else:
            whitelist.remove(id)
            await self.config.whitelist.set(whitelist)
            await ctx.send(f"Removed `{id}` from the whitelist.")

    @guildmanager.command(name="clear")
    async def guildmanager_clear(self, ctx: Context):
        """
        Remove all guilds from the whitelist.
        """
        whitelist = await self.config.whitelist()
        if not whitelist:
            await ctx.send("There are no guilds in the whitelist.")
            return
        await self.config.whitelist.clear()
        await ctx.send("Cleared the whitelist.")

    @guildmanager.command(name="list")
    async def guildmanager_list(self, ctx: Context):
        """
        List all of the guilds in the whitelist.
        """
        whitelist = await self.config.whitelist()

        if not whitelist:
            await ctx.send("There are no guilds in the whitelist.")
            return

        embeds = []

        m = ""
        for guild_id in whitelist:
            guild = self.bot.get_guild(guild_id)
            guild_name = guild.name if guild else "Unknown Guild"
            m += f"{guild_name} - {guild_id}\n"

        pages = [p for p in pagify(m, page_length=1024)]

        for i, page in enumerate(pages):
            embed = discord.Embed(
                title="Whitelisted Guilds",
                description=page,
                color=await self.bot.get_embed_colour(ctx.channel),
            )
            if len(pages) > 1:
                embed.set_footer(text=f"Page {i + 1}/{len(pages)}")
            embeds.append(embed)

        if len(embeds) > 1:
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            await ctx.send(embed=embeds[0])
