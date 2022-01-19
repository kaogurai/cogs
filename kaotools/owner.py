from copy import copy

import discord
from redbot.cogs.downloader.converters import InstalledCog
from redbot.core import commands
from redbot.core.utils.chat_formatting import box, humanize_list

from .abc import MixinMeta


class OwnerCommands(MixinMeta):
    @commands.is_owner()
    @commands.command()
    async def updr(self, ctx, *cogs: InstalledCog):
        """Update cogs without questioning about reload."""
        ctx.assume_yes = True
        cog_update_command = ctx.bot.get_command("cog update")
        if not cog_update_command:
            await ctx.send("Downloader isn't loaded.")
            return
        await ctx.invoke(cog_update_command, *cogs)

    @commands.command()
    @commands.is_owner()
    async def unusedrepos(self, ctx):
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
        await ctx.send(f"Unused: \n" + box(humanize_list(repos), lang="py"))

    @commands.command()
    @commands.is_owner()
    @commands.bot_has_permissions(attach_files=True)
    async def deezerdl(self, ctx, *, song: str):
        """
        Download a song from Deezer.
        """
        tracks = await self.deezerclient.search("track", song)
        if not tracks:
            return await ctx.send("I couldn't find anything for your query.")
        track = tracks[0]
        if int(track["FILESIZE"]) > 8000000:
            return await ctx.send("Sorry, that song is too big to download.")
        title = track["SNG_TITLE"]
        artist = track["ART_NAME"]
        name = f"{artist} - {title}.mp3"
        await ctx.send(f"Downloading {title} by {artist}...")
        async with ctx.typing():
            binary = await self.deezerclient.download(track)
            await ctx.send(file=discord.File(fp=binary, filename=name))

    @commands.command()
    @commands.is_owner()
    @commands.bot_has_permissions(attach_files=True)
    async def deezerplay(self, ctx, *, song: str):
        """
        Play a song from Deezer.
        """
        tracks = await self.deezerclient.search("track", song)
        if not tracks:
            return await ctx.send("I couldn't find anything for your query.")
        track = tracks[0]
        if int(track["FILESIZE"]) > 8000000:
            return await ctx.send("Sorry, that song is too big to download.")
        title = track["SNG_TITLE"]
        artist = track["ART_NAME"]
        await ctx.send(f"Playing {title} by {artist}...")
        async with ctx.typing():
            binary = await self.deezerclient.download(track)
            m = await ctx.send(file=discord.File(fp=binary, filename=f"{title}.mp3"))
        url = m.attachments[0].url
        msg = copy(ctx.message)
        msg.author = ctx.author
        msg.content = ctx.prefix + f"play {url}"

        ctx.bot.dispatch("message", msg)
