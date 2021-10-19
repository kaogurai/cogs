import discord
from redbot.core import Config, commands
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils.predicates import MessagePredicate


class AliasInjector(commands.Cog):
    """Injects aliases into the discord.py command objects."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=11133329439)
        # Key: command name (str) | Value: alias list((str))
        self.config.register_global(aliases={})

    async def reload_aliases(self):
        aliases = await self.config.aliases()
        for command in aliases.keys():
            existing = self.bot.get_command(command).aliases
            new = aliases[command]
            if new not in existing:
                self.bot.get_command(command).aliases.append(new)


    @commands.group()
    @commands.is_owner()
    async def aliasinjector(self, ctx):
        """
        Injects aliases into the discord.py command objects.
        """
        pass

    @aliasinjector.command()
    async def add(self, ctx, alias, *, command):
        """
        Adds an alias to a command.
        """
        if len(alias) > 50:
            await ctx.send("Alias must be 50 characters or less.")
            return
        command = self.bot.get_command(command)
        if not command:
            await ctx.send("That command doesn't exist.")
            return
        if alias in command.aliases:
            await ctx.send("That alias already exists.")
            return
        a = await self.config.aliases()
        aliases = a.get(command.qualified_name, [])
        aliases.append(alias)
        await self.config.aliases.set(a)
        await self.reload_aliases()
        await ctx.send(f"Added alias `{alias}` to `{command.qualified_name}`.")


    @aliasinjector.command()
    async def remove(self, ctx, alias, *, command):
        """
        Removes an alias from a command.
        """
        command = self.bot.get_command(command)
        if not command:
            await ctx.send("That command doesn't exist.")
            return
        if alias not in command.aliases:
            await ctx.send("That alias doesn't exist.")
            return
        self.bot.get_command(command).aliases.remove(alias)
        a = await self.config.aliases()
        a[command.name] = command.aliases.remove(alias)
        await self.config.aliases.set(a)

    @aliasinjector.command()
    async def clear(self, ctx):
        """
        Clears all monkeypatched aliases.
        """

    @aliasinjector.command()
    async def list(self, ctx):
        """
        Lists all monkeypatched aliases.
        """


