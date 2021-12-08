import os

from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify

from .abc import MixinMeta


class SFXConfigMixin(MixinMeta):

    @commands.command()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def addsfx(self, ctx, name: str, link: str = None):
        """
        Adds a new SFX to this guild.
        Either upload the file as a Discord attachment or use a link.

        Syntax:`[p]addsfx <name>` or `[p]addsfx <name> <link>`.
        """
        guild_sounds = await self.config.guild(ctx.guild).sounds()

        attachments = ctx.message.attachments
        if len(attachments) > 1 or (attachments and link):
            await ctx.send("Please only try to add one SFX at a time.")
            return

        url = ""
        filename = ""
        if attachments:
            attachment = attachments[0]
            url = attachment.url
        elif link:
            url = "".join(link)
        else:
            await ctx.send(
                "You must provide either a Discord attachment or a direct link to a sound."
            )
            return

        filename = "".join(url.split("/")[-1:]).replace("%20", "_")
        file_name, file_extension = os.path.splitext(filename)

        if file_extension not in [".wav", ".mp3"]:
            await ctx.send(
                "Sorry, only SFX in .mp3 and .wav format are supported at this time."
            )
            return

        if name in guild_sounds.keys():
            await ctx.send(
                f"A sound with that filename already exists. Either choose a new name or use {ctx.clean_prefix}delsfx to remove it."
            )
            return

        guild_sounds[name] = url
        await self.config.guild(ctx.guild).sounds.set(guild_sounds)

        await ctx.send("Sound added.")

    @commands.command()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def delsfx(self, ctx, soundname: str):
        """
        Deletes an existing sound.
        """

        guild_sounds = await self.config.guild(ctx.guild).sounds()

        if soundname not in guild_sounds.keys():
            await ctx.send(
                f"That sound does not exist. Try `{ctx.prefix}listsfx` for a list."
            )
            return

        del guild_sounds[soundname]
        await self.config.guild(ctx.guild).sounds.set(guild_sounds)

        await ctx.send(f"Sound deleted.")

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def addglobalsfx(self, ctx, name: str, link: str = None):
        """
        Adds a new SFX to this the bot globally.
        Either upload the file as a Discord attachment or use a link.

        Syntax:`[p]addsfx <name>` or `[p]addsfx <name> <link>`.
        """
        global_sounds = await self.config.sounds()

        attachments = ctx.message.attachments
        if len(attachments) > 1 or (attachments and link):
            await ctx.send("Please only try to add one SFX at a time.")
            return

        url = ""
        if attachments:
            attachment = attachments[0]
            url = attachment.url
        elif link:
            url = "".join(link)
        else:
            await ctx.send(
                "You must provide either a Discord attachment or a direct link to a sound."
            )
            return

        filename = "".join(url.split("/")[-1:]).replace("%20", "_")
        file_name, file_extension = os.path.splitext(filename)

        if file_extension not in [".wav", ".mp3"]:
            await ctx.send(
                "Sorry, only SFX in .mp3 and .wav format are supported at this time."
            )
            return

        if name in global_sounds.keys():
            await ctx.send(
                f"A sound with that filename already exists. Either choose a new name or use {ctx.clean_prefix}delglobalsfx to remove it."
            )
            return

        global_sounds[name] = link
        await self.config.sounds.set(global_sounds)

        await ctx.send("Sound added.")

    @commands.command()
    @commands.is_owner()
    async def delglobalsfx(self, ctx, name: str):
        """
        Deletes an existing global sound.
        """

        global_sounds = await self.config.sounds()

        if name not in global_sounds.keys():
            await ctx.send(
                f"That sound does not exist. Try `{ctx.prefix}listsfx` for a list."
            )
            return

        del global_sounds[name]
        await self.config.sounds.set(global_sounds)

        await ctx.send(f"Sound deleted.")

    @commands.command()
    @commands.guild_only()
    async def listsfx(self, ctx):
        """
        Lists all available sounds for this server.
        """

        guild_sounds = await self.config.guild(ctx.guild).sounds()
        global_sounds = await self.config.sounds()

        if (len(guild_sounds.items()) + len(global_sounds.items())) == 0:
            await ctx.send(f"No sounds found. Use `{ctx.prefix}addsfx` to add one.")
            return

        txt = ""

        if guild_sounds:
            txt += "**Guild Sounds**:\n"
            for sound in guild_sounds:
                txt += sound + "\n"

        if global_sounds:
            txt += "\n**Global Sounds**:\n"
            for sound in global_sounds:
                if guild_sounds and sound in guild_sounds:
                    txt += sound + " (disabled)\n"
                txt += sound + "\n"

        pages = [p for p in pagify(text=txt, delims="\n")]

        for page in pages:
            await ctx.send(page)
