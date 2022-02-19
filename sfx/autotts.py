import contextlib

import discord
from redbot.core import commands

from .abc import MixinMeta


class AutoTTSMixin(MixinMeta):
    @commands.command()
    @commands.guild_only()
    async def autotts(self, ctx, guild_setting: bool = None):
        """
        This command is used to toggle the auto tts feature.

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

            if guild_setting:
                await self.config.guild(ctx.guild).allow_autotts.set(True)
                await ctx.send("AutoTTS is now allowed for this guild.")
            else:
                await self.config.guild(ctx.guild).allow_autotts.set(False)
                await ctx.send("AutoTTS is now disallowed for this guild.")

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if (
            message.author.id not in self.autotts
            or not message.guild
            or message.author.bot
            or not await self.bot.allowed_by_whitelist_blacklist(who=message.author)
            or await self.bot.cog_disabled_in_guild(self, message.guild)
        ):
            return

        toggle = await self.config.guild(message.guild).allow_autotts()
        if not toggle:
            return
        if not message.author.voice or not message.author.voice.channel:
            return

        author_data = await self.config.user(message.author).all()
        author_voice = author_data["voice"]
        author_translate = author_data["translate"]

        is_voice = self.get_voice(author_voice)
        if not is_voice:
            await self.config.user(message.author).voice.clear()
            author_voice = await self.config.user(message.author).voice()

        url = self.generate_url(author_voice, author_translate, message.clean_content)

        track_info = ("Text to Speech", message.author)
        await self.play_sound(
            message.author.voice.channel,
            message.channel,
            "autotts",
            url,
            track_info,
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
