import asyncio

import discord
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils.predicates import MessagePredicate


class AliasInjector(commands.Cog):
    """
    Injects aliases into the discord.py command objects.
    """

    __version__ = "1.0.7"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=11133329439)
        # Key: command name (str) | Value: alias list((str))
        self.config.register_global(aliases={})
        self.bot.loop.create_task(self.reload_aliases())

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def reload_aliases(self):
        aliases = await self.config.aliases()
        for command in aliases.keys():
            command_obj = self.bot.get_command(command)
            if not command_obj:
                continue
            new = aliases[command]
            for alias in new:
                if alias not in command_obj.aliases:
                    self.bot.remove_command(command_obj.qualified_name)
                    command_obj.aliases.append(alias)
                    self.bot.add_command(command_obj)

    async def remove_aliases(self):
        aliases = await self.config.aliases()
        for command in aliases.keys():
            a = aliases[command]
            command_obj = self.bot.get_command(command)
            if command_obj:
                try:
                    self.bot.remove_command(command_obj.qualified_name)
                except ValueError:
                    continue
                for alias in a:
                    command_obj.aliases.remove(alias)
                self.bot.add_command(command_obj)

    def cog_unload(self):
        self.bot.loop.create_task(self.remove_aliases())

    @commands.Cog.listener()
    async def on_cog_add(self, cog):
        if cog.__class__.__name__ != self.__class__.__name__:
            await self.reload_aliases()

    @commands.group()
    @commands.is_owner()
    async def aliasinjector(self, ctx):
        """
        Injects aliases into the discord.py command objects.
        """
        pass

    @aliasinjector.command()
    async def add(self, ctx, alias, *, command_name):
        """
        Adds an alias to a command.
        """
        if len(alias) > 60:
            await ctx.send("Alias must be 60 characters or less.")
            return
        command = self.bot.get_command(command_name)
        if not command:
            await ctx.send("That command doesn't exist.")
            return
        if alias in command.aliases:
            await ctx.send("That alias already exists.")
            return
        a = await self.config.aliases()
        aliases = a.get(command_name, [])
        aliases.append(alias)
        a[command_name] = aliases
        await self.config.aliases.set(a)
        await self.reload_aliases()
        await ctx.send(f"Added alias `{alias}` to `{command_name}`.")

    @aliasinjector.command()
    async def remove(self, ctx, alias, *, command_name):
        """
        Removes an alias from a command.
        """
        command = self.bot.get_command(command_name)
        if not command:
            await ctx.send("That command doesn't exist.")
            return
        a = await self.config.aliases()
        aliases = a.get(command_name, [])
        if alias not in aliases:
            await ctx.send("That alias doesn't exist.")
            return
        if command:
            self.bot.remove_command(command_name)
            command.aliases.remove(alias)
            self.bot.add_command(command)
        aliases.remove(alias)
        a[command_name] = aliases
        await self.config.aliases.set(a)
        await ctx.send(f"Removed alias `{alias}` from `{command_name}`.")

    @aliasinjector.command()
    async def clear(self, ctx):
        """
        Clears all monkeypatched aliases.
        """
        a = await self.config.aliases()
        if not a:
            await ctx.send("There are no aliases to clear.")
            return
        try:
            await ctx.send(
                "Are you sure you want to clear all the monkeypatched aliases? Respond with yes or no."
            )
            predictate = MessagePredicate.yes_or_no(ctx, user=ctx.author)
            await ctx.bot.wait_for("message", check=predictate, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send(
                "You never responded, please use the command again to clear all the aliases."
            )
            return
        if predictate.result:
            for command in a.keys():
                monkeypatched_ones = a[command]
                command_obj = self.bot.get_command(command)
                if command_obj:
                    self.bot.remove_command(command_obj.qualified_name)
                    for alias in monkeypatched_ones:
                        command_obj.aliases.remove(alias)
                    self.bot.add_command(command_obj)
            await self.config.aliases.clear()
            await ctx.send("Cleared all aliases.")
        else:
            await ctx.send("Ok, I won't clear any aliases.")

    @aliasinjector.command()
    async def list(self, ctx):
        """
        Lists all monkeypatched aliases.
        """
        a = await self.config.aliases()
        if not a:
            await ctx.send("There are no aliases to list.")
            return
        text = ""
        for command in a.keys():
            if a[command]:
                text += f"**{command}** - {humanize_list(a[command])}\n"
        if not text:
            await ctx.send("There are no aliases to list.")
            return
        pages = [p for p in pagify(text=text, delims="\n")]
        embeds = []
        for index, page in enumerate(pages):
            embed = discord.Embed(
                title="Monkeypatched Aliases",
                color=await ctx.embed_colour(),
                description=page,
            )
            if len(embeds) > 1:
                embed.set_footer(text=f"Page {index+1}/{len(pages)}")
            embeds.append(embed)

        if len(pages) == 1:
            await ctx.send(embed=embeds[0])
        else:
            await menu(ctx, embeds, DEFAULT_CONTROLS, timeout=60)
