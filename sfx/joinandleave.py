from typing import Optional

import discord
from redbot.core import commands
from redbot.core.commands import Context

from .abc import MixinMeta


class JoinAndLeaveMixin(MixinMeta):
    @commands.Cog.listener(name="on_voice_state_update")
    async def joinleave_voice_listener(
        self,
        user: discord.Member,
        before: Optional[discord.VoiceChannel],
        after: Optional[discord.VoiceChannel],
    ):
        """
        Listens for users joining and leaving voice channels and plays sounds if configured.
        """
        if user.bot:
            return
        if await self.bot.allowed_by_whitelist_blacklist(who=user) is False:
            return
        if await self.bot.cog_disabled_in_guild(self, user.guild):
            return

        guild_config = await self.config.guild(user.guild).all()
        if not guild_config["allow_join_and_leave"]:
            return
        if user.id in guild_config["disabled_users"]:
            return

        user_config = await self.config.user(user).all()

        # Check the priority setting
        if guild_config["priority"] == "guild":
            # Play guild sounds if available, otherwise play user sounds
            if guild_config["join_sound"] and before.channel is None and after.channel:
                current_perms = after.channel.permissions_for(user.guild.me)
                if not current_perms.speak or not current_perms.connect:
                    return

                if user.guild.me and user.guild.me.voice:
                    if after.channel != user.guild.me.voice.channel:
                        return

                track_info = ("Join Sound", user)

                await self.play_sound(
                    after.channel,
                    None,
                    "joinleave",
                    guild_config["join_sound"],
                    track_info,
                )
                return
            elif (
                guild_config["leave_sound"] and before.channel and after.channel is None
            ):
                current_perms = before.channel.permissions_for(user.guild.me)
                if not current_perms.speak or not current_perms.connect:
                    return

                if user.guild.me and user.guild.me.voice:
                    if before.channel != user.guild.me.voice.channel:
                        return

                track_info = ("Leave Sound", user)
                await self.play_sound(
                    before.channel,
                    None,
                    "joinleave",
                    guild_config["leave_sound"],
                    track_info,
                )
                return
            elif user_config["join_sound"] and before.channel is None and after.channel:
                current_perms = after.channel.permissions_for(user.guild.me)
                if not current_perms.speak or not current_perms.connect:
                    return

                if user.guild.me and user.guild.me.voice:
                    if after.channel != user.guild.me.voice.channel:
                        return

                track_info = ("Join Sound", user)

                await self.play_sound(
                    after.channel,
                    None,
                    "joinleave",
                    user_config["join_sound"],
                    track_info,
                )
                return
            elif (
                user_config["leave_sound"] and before.channel and after.channel is None
            ):
                current_perms = before.channel.permissions_for(user.guild.me)
                if not current_perms.speak or not current_perms.connect:
                    return

                if user.guild.me and user.guild.me.voice:
                    if before.channel != user.guild.me.voice.channel:
                        return

                track_info = ("Leave Sound", user)
                await self.play_sound(
                    before.channel,
                    None,
                    "joinleave",
                    user_config["leave_sound"],
                    track_info,
                )
                return
        else:
            # Play user sounds if available, otherwise play guild sounds
            if user_config["join_sound"] and before.channel is None and after.channel:
                current_perms = after.channel.permissions_for(user.guild.me)
                if not current_perms.speak or not current_perms.connect:
                    return

                if user.guild.me and user.guild.me.voice:
                    if after.channel != user.guild.me.voice.channel:
                        return

                track_info = ("Join Sound", user)

                await self.play_sound(
                    after.channel,
                    None,
                    "joinleave",
                    user_config["join_sound"],
                    track_info,
                )
                return
            elif (
                user_config["leave_sound"] and before.channel and after.channel is None
            ):
                current_perms = before.channel.permissions_for(user.guild.me)
                if not current_perms.speak or not current_perms.connect:
                    return

                if user.guild.me and user.guild.me.voice:
                    if before.channel != user.guild.me.voice.channel:
                        return

                track_info = ("Leave Sound", user)
                await self.play_sound(
                    before.channel,
                    None,
                    "joinleave",
                    user_config["leave_sound"],
                    track_info,
                )
                return
            elif (
                guild_config["join_sound"] and before.channel is None and after.channel
            ):
                current_perms = after.channel.permissions_for(user.guild.me)
                if not current_perms.speak or not current_perms.connect:
                    return

                if user.guild.me and user.guild.me.voice:
                    if after.channel != user.guild.me.voice.channel:
                        return

                track_info = ("Join Sound", user)

                await self.play_sound(
                    after.channel,
                    None,
                    "joinleave",
                    guild_config["join_sound"],
                    track_info,
                )
                return
            elif (
                guild_config["leave_sound"] and before.channel and after.channel is None
            ):
                current_perms = before.channel.permissions_for(user.guild.me)
                if not current_perms.speak or not current_perms.connect:
                    return

                if user.guild.me and user.guild.me.voice:
                    if before.channel != user.guild.me.voice.channel:
                        return

                track_info = ("Leave Sound", user)
                await self.play_sound(
                    before.channel,
                    None,
                    "joinleave",
                    guild_config["leave_sound"],
                    track_info,
                )
                return

    @commands.group(aliases=["joinleave"])
    async def joinandleave(self, ctx: Context):
        """Settings for join and leave sounds."""
        pass

    @joinandleave.group(name="guild")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def joinandleave_guild(self, ctx: Context):
        """
        Commands for configuring join and leave sounds for this server.
        """
        pass

    @joinandleave_guild.command(name="priority")
    async def joinandleave_guild_priority(self, ctx: Context):
        """
        Toggle the priority between guild sounds and user sounds.
        """
        current_priority = await self.config.guild(ctx.guild).priority()
        if current_priority == "user":
            await self.config.guild(ctx.guild).priority.set("guild")
            await ctx.send(
                "The priority for join and leave sounds is now set to guild sounds."
            )
        else:
            await self.config.guild(ctx.guild).priority.set("user")
            await ctx.send(
                "The priority for join and leave sounds is now set to user sounds."
            )

    @joinandleave_guild.command(name="setjoin")
    async def joinandleave_guild_setjoin(self, ctx, url: Optional[str] = None):
        """
        Set the join sound for this server.

        If this is set, the bot will play this sound when a user joins a voice channel and user's set join sounds will NOT play.

        If you don't provide a URL, it will clear the sound and now play user's set join sounds, assuming `joinandleave guild toggle` is on.
        """
        if not url:
            attachments = ctx.message.attachments
            if not attachments:
                await self.config.guild(ctx.guild).join_sound.clear()
                return await ctx.send("I've reset this guild's join sound.")
            url = attachments[0].url

        await self.config.guild(ctx.guild).join_sound.set(url)
        await ctx.send(
            "I've set the sound that will be played upon everyone joining a voice channel."
        )

    @joinandleave_guild.command(name="setleave")
    async def joinandleave_guild_setleave(
        self, ctx: Context, url: Optional[str] = None
    ):
        """
        Set the leave sound for this server.

        If this is set, the bot will play this sound when a user leave a voice channel and user's set leave sounds will NOT play.

        If you don't provide a URL, it will clear the sound and now play user's set leave sounds, assuming `joinandleave guild toggle` is on.
        """
        if not url:
            attachments = ctx.message.attachments
            if not attachments:
                await self.config.guild(ctx.guild).leave_sound.clear()
                return await ctx.send("I've reset this guild's leave sound.")
            url = attachments[0].url

        await self.config.guild(ctx.guild).leave_sound.set(url)
        await ctx.send(
            "I've set the sound that will be played upon everyone leaving a voice channel."
        )

    @joinandleave_guild.command(name="toggle")
    async def joinandleave_guild_toggle(self, ctx: Context):
        """
        Toggle join and leave sounds being played in voice channels in this server.
        """
        conf = await self.config.guild(ctx.guild).allow_join_and_leave()
        await self.config.guild(ctx.guild).allow_join_and_leave.set(not conf)
        await ctx.send(
            "Join and leave sounds will now be played in voice channels."
            if not conf
            else "Join and leave sounds will no longer be played in voice channels."
        )

    @joinandleave_guild.command(name="disableuser")
    async def joinandleave_guild_disableuser(self, ctx: Context, user: discord.Member):
        """
        Disable join/leave sounds for a specific user in this server.
        """
        disabled_users = await self.config.guild(ctx.guild).disabled_users()
        if user.id in disabled_users:
            await ctx.send(f"{user.mention}'s join/leave sounds are already disabled.")
        else:
            disabled_users.append(user.id)
            await self.config.guild(ctx.guild).disabled_users.set(disabled_users)
            await ctx.send(f"{user.mention}'s join/leave sounds have been disabled.")

    @joinandleave_guild.command(name="enableuser")
    async def joinandleave_guild_enableuser(self, ctx: Context, user: discord.Member):
        """
        Enable join/leave sounds for a specific user in this server.
        """
        disabled_users = await self.config.guild(ctx.guild).disabled_users()
        if user.id not in disabled_users:
            await ctx.send(f"{user.mention}'s join/leave sounds are not disabled.")
        else:
            disabled_users.remove(user.id)
            await self.config.guild(ctx.guild).disabled_users.set(disabled_users)
            await ctx.send(f"{user.mention}'s join/leave sounds have been enabled.")

    @joinandleave.command()
    async def setjoin(self, ctx: Context, url: Optional[str] = None):
        """
        Set the sound that plays when you join a voice channel.

        Providing no attachment or URL will clear the current sound.
        """
        if not url:
            attachments = ctx.message.attachments
            if not attachments:
                await self.config.user(ctx.author).join_sound.clear()
                return await ctx.send("I've reset your join sound.")
            url = attachments[0].url

        await self.config.user(ctx.author).join_sound.set(url)
        await ctx.send(
            "I've set your sound that will be played upon you joining a voice channel."
        )

    @joinandleave.command()
    async def setleave(self, ctx: Context, url: Optional[str] = None):
        """
        Set the sound that plays when you leave a voice channel.

        Providing no attachment or URL will clear the current sound.
        """
        if not url:
            attachments = ctx.message.attachments
            if not attachments:
                await self.config.user(ctx.author).leave_sound.clear()
                return await ctx.send("I've reset your leave sound.")
            url = attachments[0].url

        await self.config.user(ctx.author).join_sound.set(url)
        await ctx.send(
            "I've set your sound that will be played upon you leaving a voice channel."
        )
