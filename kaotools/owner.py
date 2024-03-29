import discord
from redbot.cogs.downloader.converters import InstalledCog
from redbot.core import commands
from redbot.core.commands import Context

from .abc import MixinMeta


class OwnerCommands(MixinMeta):
    @commands.is_owner()
    @commands.command()
    async def updr(self, ctx: Context, *cogs: InstalledCog):
        """Update cogs without questioning about reload."""
        ctx.assume_yes = True
        cog_update_command = ctx.bot.get_command("cog update")
        if not cog_update_command:
            await ctx.send("Downloader isn't loaded.")
            return
        await ctx.invoke(cog_update_command, *cogs)

    @commands.command()
    @commands.is_owner()
    async def unusedrepos(self, ctx: Context):
        """View unused downloader repos."""
        repo_cog = self.bot.get_cog("Downloader")
        if not repo_cog:
            return await ctx.send("Downloader cog not found.")
        repos = [r.name for r in repo_cog._repo_manager.repos]
        active_repos = {c.repo_name for c in await repo_cog.installed_cogs()}
        for r in active_repos:
            try:
                repos.remove(r)
            except:
                pass
        if not repos:
            await ctx.send("All repos are currently being used!")
            return

        embed = discord.Embed(title="Unused repos", description="\n".join(repos))
        await ctx.send(embed=embed)
