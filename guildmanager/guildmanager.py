import contextlib

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu


class GuildManager(commands.Cog):
    """
    Allows you to whitelist servers that you want to use the bot in.
    """

    __version__ = "1.0.3"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=567856)
        default_global = {
            "whitelist": [],
            "special_whitelist": [],
            "toggle": False,
        }
        self.config.register_global(**default_global)
        self.bot.loop.create_task(self.ensure_requirements())

    def cog_unload(self):
        self.bot.loop.create_task(self.ensure_requirements())

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx: Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def ensure_requirements(self) -> None:
        toggle = await self.config.toggle()
        if not toggle:
            return

        for guild in self.bot.guilds:
            if not guild:
                continue  # In case the guild hasn't loaded yet, idk
            if guild.id in await self.config.whitelist() or guild.id in await self.config.special_whitelist():
                continue

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

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if not guild:
            return
        if guild.id in await self.config.whitelist() or guild.id in await self.config.special_whitelist():
            return

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
            await self.config.toggle.set(False)
            await ctx.send("The guild manager is now disabled.")
        else:
            await self.config.toggle.set(True)
            await ctx.send(f"The guild manager is now enabled. I will leave any servers that aren't whitelisted on cog load, cog unload, and the invokation of the `{ctx.clean_prefix}guildmanager whitelist` command. Please either disable the guild manager or whitelist the servers you want to use the bot in now.")

    @guildmanager.command(name="enforce")
    async def guildmanager_enforce(self, ctx: Context):
        """
        Enforce guild requirements.
        """
        await self.ensure_requirements()
        await ctx.tick()

    @guildmanager.command(name="add")
    async def guildmanager_add(self, ctx: Context, id: int, special: bool = False):
        """
        Add a guild to the whitelist.

        `id`: The ID of the guild.
        `special`: Whether or not this is a special guild.
        """
        whitelist = await self.config.whitelist()
        special_whitelist = await self.config.special_whitelist()

        if id in whitelist or id in special_whitelist:
            await ctx.send("This guild is already in the whitelist.")
            return

        if special:
            special_whitelist.append(id)
            await self.config.special_whitelist.set(special_whitelist)
            await ctx.send(f"Added `{id}` to the special whitelist.")
        else:
            whitelist.append(id)
            await self.config.whitelist.set(whitelist)
            await ctx.send(f"Added `{id}` to the whitelist.")

    @guildmanager.command(name="remove")
    async def guildmanager_remove(self, ctx: Context, id: int):
        """
        Remove a guild from the whitelist.

        `id`: The ID of the guild.
        """
        whitelist = await self.config.whitelist()
        special_whitelist = await self.config.special_whitelist()

        if id not in whitelist and id not in special_whitelist:
            await ctx.send("This guild is not in the whitelist.")
            return

        if id in special_whitelist:
            special_whitelist.remove(id)
            await self.config.special_whitelist.set(special_whitelist)
            await ctx.send(f"Removed `{id}` from the special whitelist.")
        else:
            whitelist.remove(id)
            await self.config.whitelist.set(whitelist)
            await ctx.send(f"Removed `{id}` from the whitelist.")

    @guildmanager.command(name="list")
    async def guildmanager_list(self, ctx: Context):
        """
        List all the guilds in the whitelist.
        """
        whitelist = await self.config.whitelist()
        special_whitelist = await self.config.special_whitelist()

        if not whitelist and not special_whitelist:
            await ctx.send("There are no guilds in the whitelist.")
            return

        embeds = []

        m = "**Special Guilds:**\n"
        for guild_id in special_whitelist:
            guild = self.bot.get_guild(guild_id)
            guild_name = guild.name if guild else "Unknown Guild"
            m += f"{guild_name} - {guild_id}\n"

        m += "\n**Other Guilds:**\n"
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
