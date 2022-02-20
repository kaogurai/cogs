import contextlib

import discord
from redbot.core import commands

from .abc import MixinMeta


class AutoTTSMixin(MixinMeta):
    @commands.command()
    @commands.guild_only()
    async def autotts(self, ctx, guild_setting: bool = None):
        """
        Toggles the AutoTTS feature.

        If you don't provide any arguments, it will toggle the setting for you.

        If you provide a boolean, it will set the setting for the guild to that value. (mod/admin only)
        """
        toggle = await self.config.guild(ctx.guild).allow_autotts()
        if type(guild_setting) is not bool:
            if ctx.author.id in self.autotts:
                self.autotts.remove(ctx.author.id)
                await ctx.send("I will no longer automatically say your messages as TTS.")
            else:
                if not toggle:
                    await ctx.send("AutoTTS is disallowed on this server.")
                    return
                self.autotts.append(ctx.author.id)
                await ctx.send("I will now automatically say your messages as TTS.")
        else:
            if ctx.author.has_permissions(manage_guild=True):
                if guild_setting:
                    await self.config.guild(ctx.guild).allow_autotts.set(True)
                    await ctx.send("AutoTTS is now allowed for this guild.")
                else:
                    await self.config.guild(ctx.guild).allow_autotts.set(False)
                    await ctx.send("AutoTTS is now disallowed for this guild.")
            else:
                await ctx.send(
                    "You need the `Manage Server` permission to use this command."
                )

    @commands.Cog.listener(name="on_message_without_command")
    async def autotts_listener(self, message: discord.Message):
        if (
            message.author.id not in self.autotts
            or not message.guild
            or message.author.bot
            or not await self.bot.allowed_by_whitelist_blacklist(who=message.author)
            or await self.bot.cog_disabled_in_guild(self, message.guild)
            or not await self.config.guild(message.guild).allow_autotts()
            or not message.author.voice
            or not message.author.voice.channel
        ):
            return

        await self.play_tts(
            message.author,
            message.author.voice.channel,
            message.channel,
            message.clean_content,
        )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if (
            member.bot
            or not await self.bot.allowed_by_whitelist_blacklist(who=member)
            or await self.bot.cog_disabled_in_guild(self, member.guild)
            or member.id not in self.autotts
        ):
            return
        if before.channel and not after.channel:
            self.autotts.remove(member.id)
            embed = discord.Embed(
                title="AutoTTS Disabled",
                color=await self.bot.get_embed_color(member.guild),
            )
            embed.description = (
                f"You have left {before.channel.mention} and therefor AutoTTS has been disabled.\n\n"
                f"If you would like to re-enable AutoTTS, please join a voice channel and rerun the autotts command."
            )
            with contextlib.suppress(discord.HTTPException):
                await member.send(embed=embed)
