import contextlib
from typing import Optional

import discord
from redbot.core import commands
from redbot.core.commands import Context

from .abc import MixinMeta


class AutoTTSMixin(MixinMeta):
    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def autotts(self, ctx: Context):
        """
        Toggles the AutoTTS feature.

        If the server subcommand isn't used, it will toggle it for yourself.
        """
        toggle = await self.config.guild(ctx.guild).allow_autotts()
        if ctx.author.id in self.autotts:
            self.autotts.remove(ctx.author.id)
            await ctx.send("I will no longer automatically say your messages as TTS.")
        else:
            if not toggle:
                await ctx.send("AutoTTS is disallowed on this server.")
                return
            self.autotts.append(ctx.author.id)
            await ctx.send("I will now automatically say your messages as TTS.")

    @autotts.command(name="server")
    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def autotts_server(self, ctx: Context):
        """Toggles the AutoTTS feature for the server."""
        toggle = await self.config.guild(ctx.guild).allow_autotts()
        if toggle:
            await self.config.guild(ctx.guild).allow_autotts.set(False)
            await ctx.send("AutoTTS is now disallowed for this server.")
        else:
            await self.config.guild(ctx.guild).allow_autotts.set(True)
            await ctx.send("AutoTTS is now allowed for this server.")

    @commands.Cog.listener(name="on_message_without_command")
    async def autotts_message_listener(self, message: discord.Message):
        if (
            message.author.id not in self.autotts
            or not message.guild
            or message.author.bot
            or not await self.bot.allowed_by_whitelist_blacklist(who=message.author)
            or await self.bot.cog_disabled_in_guild(self, message.guild)
            or not await self.config.guild(message.guild).allow_autotts()
            or not message.author.voice
            or not message.author.voice.channel
            or not message.author.voice.channel.permissions_for(message.author).speak
            or not await self.can_tts(message)
        ):
            return

        await self.play_tts(
            message.author,
            message.author.voice.channel,
            message.channel,
            "autotts",
            message.clean_content,
        )

    @commands.Cog.listener(name="on_voice_state_update")
    async def autotts_voice_listener(
        self,
        member: discord.Member,
        before: Optional[discord.VoiceChannel],
        after: Optional[discord.VoiceChannel],
    ):
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
                f"You have left {before.channel.mention} and therefore AutoTTS has been disabled.\n\n"
                f"If you would like to re-enable AutoTTS, please join a voice channel and rerun the autotts command."
            )
            with contextlib.suppress(discord.HTTPException):
                await member.send(embed=embed)
