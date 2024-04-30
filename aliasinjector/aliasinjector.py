import asyncio

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import BadArgument, Command, Context
from redbot.core.utils.chat_formatting import humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils.predicates import MessagePredicate


class AliasInjector(commands.Cog):
    """
    Injects aliases into the command objects.
    """

    __version__ = "3.0.1"

    def __init__(self, bot: Red):
        """
        Initalizes the cog by setting up the datastore and loading aliases.
        """
        self.bot = bot
        self.config = Config.get_conf(self, identifier=11133329439)
        self.config.register_global(aliases={})
        self.bot.loop.create_task(self.load_aliases())

    async def red_delete_data_for_user(self, **kwargs):
        """
        This cog does not store any user data.
        """
        return

    def format_help_for_context(self, ctx: Context) -> str:
        """
        Adds the cog version to the help menu.
        """
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    def cog_unload(self):
        """
        Removes injected aliases when cog is unloaded.
        """
        self.bot.loop.create_task(self.remove_aliases())

    @commands.Cog.listener()
    async def on_cog_add(self, cog: commands.Cog):
        """
        Reloads aliases upon a cog being added.
        """
        if cog.__class__.__name__ != self.__class__.__name__:
            await self.remove_aliases()
            await self.load_aliases()

    async def load_aliases(self) -> None:
        """
        Injects all aliases into the command objects.
        """
        aliases = await self.config.aliases()

        for command, aliases in aliases.items():
            for alias in aliases:
                command_obj = self.bot.get_command(command)
                if command_obj is None:
                    continue
                if not self.bot.get_command(alias):
                    self.inject_alias(alias, command_obj)

    async def remove_aliases(self) -> None:
        """
        Removes all injected aliases from the command objects.
        """
        aliases = await self.config.aliases()

        for command, aliases in aliases.items():
            for alias in aliases:
                command_obj = self.bot.get_command(command)
                self.remove_alias(alias, command_obj)

    def inject_alias(self, alias: str, command_obj: Command) -> None:
        """
        Injects an alias into the given command object.
        """
        if " " not in alias:
            command_obj.aliases.append(alias)
            self.bot.all_commands[alias] = command_obj
        else:
            command_tree = alias.split(" ")
            new_alias = command_tree.pop()

            c = None
            for cmd in command_tree:
                if cmd == command_tree[0]:
                    c = self.bot.all_commands[cmd]
                else:
                    c = c.all_commands[cmd]

            c.all_commands[new_alias] = command_obj
            command_obj.aliases.append(new_alias)

    def remove_alias(self, alias: str, command_obj: Command) -> None:
        """
        Removes an alias from the given command object.
        """
        if " " not in alias:
            if command_obj:
                command_obj.aliases.remove(alias)
            del self.bot.all_commands[alias]
        else:
            if command_obj:
                command_tree = alias.split(" ")
                new_alias = command_tree.pop()

                c = None
                for cmd in command_tree:
                    if cmd == command_tree[0]:
                        c = self.bot.all_commands[cmd]
                    else:
                        c = c.all_commands[cmd]

                del c.all_commands[new_alias]
                command_obj.aliases.remove(new_alias)

    @commands.group()
    @commands.is_owner()
    async def aliasinjector(self, ctx: Context):
        """
        Injects aliases into the discord.py command objects.
        """
        pass

    @aliasinjector.command(usage="<command> | <alias>")
    async def add(self, ctx: Context, *, args: str):
        """
        Adds an alias to a command.

        If you want to be able to run `[p]resetqueue` by trigging the `[p]queue clear` command,
        you'd run `[p]aliasinjector add queue clear | resetqueue`, but if you wanted to be able to
        run `[p]queue reset`, you'd run  `[p]aliasinjector add queue clear | queue reset`.
        """
        split = args.split("|")
        if len(split) != 2:
            raise BadArgument()

        command = split[0].strip()
        alias = split[1].strip()

        command_obj = self.bot.get_command(command)
        if not command_obj:
            await ctx.send(f"{command} is not a valid command.")
            return

        if self.bot.get_command(alias):
            await ctx.send(f"{alias} is already an alias for {command}.")
            return

        if " " in alias and len(alias.split(" ")) > len(command.split(" ")):
            await ctx.send(
                "You can only add aliases that are the same length as the command they are aliasing."
            )
            return

        self.inject_alias(alias, command_obj)

        aliases = await self.config.aliases()
        if command not in aliases.keys():
            aliases[command] = [alias]
        else:
            aliases[command].append(alias)
        await self.config.aliases.set(aliases)
        await ctx.send(f"Added `{alias}` as an alias for `{command}`")

    @aliasinjector.command(usage="<command> | <alias>")
    async def remove(self, ctx: Context, *, args: str):
        """
        Removes an alias from a command.

        If you want to remove `[p]resetqueue` which triggers the  `[p]queue clear` command,
        you'd run `[p]aliasinjector remove queue clear | resetqueue`, but if you wanted to be
        able to remove `[p]queue reset`, you'd run  `[p]aliasinjector add queue clear | queue reset`.
        """
        split = args.split("|")
        if len(split) != 2:
            raise BadArgument()

        command = split[0].strip()
        alias = split[1].strip()

        command_obj = self.bot.get_command(command)
        if not command_obj:
            await ctx.send(f"{command} is not a valid command.")
            return

        if not self.bot.get_command(alias):
            await ctx.send(f"{alias} is not an alias for {command}.")
            return

        self.remove_alias(alias, command_obj)

        aliases = await self.config.aliases()
        aliases[command].remove(alias)
        await self.config.aliases.set(aliases)
        await ctx.send(f"Removed `{alias}` as an alias for `{command}`")

    @aliasinjector.command()
    async def clear(self, ctx: Context):
        """
        Clears all injected aliases.
        """
        a = await self.config.aliases()
        if not a:
            await ctx.send("There are no aliases to clear.")
            return

        try:
            await ctx.send(
                "Are you sure you want to clear all the injected aliases? Respond with yes or no."
            )
            predictate = MessagePredicate.yes_or_no(ctx, user=ctx.author)
            await ctx.bot.wait_for("message", check=predictate, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send(
                "You never responded, please use the command again to clear all the aliases."
            )
            return

        if predictate.result:
            await self.config.aliases.clear()
            await self.remove_aliases()
            await ctx.send("Cleared all aliases.")
        else:
            await ctx.send("Ok, I won't clear any aliases.")

    @aliasinjector.command()
    async def list(self, ctx: Context):
        """
        Lists all injected aliases.
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
                title="Injected Aliases",
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
