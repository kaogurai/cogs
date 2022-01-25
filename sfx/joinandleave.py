from redbot.core import commands

from .abc import MixinMeta


class JoinAndLeaveMixin(MixinMeta):
    @commands.Cog.listener()
    async def on_voice_state_update(self, user, before, after):
        print(user, before.channel, after.channel)

        guild_config = await self.config.guild(user.guild).all()
        if not guild_config["allow_join_and_leave"]:
            return

        user_config = await self.config.user(user).all()

        # User joins voice channel
        if user_config["join_sound"] and before.channel is None and after.channel:

            current_perms = after.channel.permissions_for(user.guild.me)
            if not current_perms.speak or not current_perms.connect:
                return

            if user.guild.me and user.guild.me.voice:
                if after.channel != user.guild.me.voice.channel:
                    return

            track_info = ("Join Sound", user)

            await self.play_sfx(
                after.channel,
                None,
                "joinleave",
                [user_config["join_sound"]],
                track_info,
            )
            return

        # User leaves voice channel entirely
        if user_config["leave_sound"] and before.channel and after.channel is None:

            current_perms = before.channel.permissions_for(user.guild.me)
            if not current_perms.speak or not current_perms.connect:
                return

            if user.guild.me and user.guild.me.voice:
                if before.channel != user.guild.me.voice.channel:
                    return

            track_info = ("Leave Sound", user)
            await self.play_sfx(
                before.channel,
                None,
                "joinleave",
                [user_config["leave_sound"]],
                track_info,
            )
            return

    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def joinandleave(self, ctx):
        """
        Toggle join and leave sounds being played in voice channels.
        """
        conf = await self.config.guild(ctx.guild).allow_join_and_leave()
        await self.config.guild(ctx.guild).allow_join_and_leave.set(not conf)
        await ctx.send(
            "Join and leave sounds will now be played in voice channels."
            if not conf
            else "Join and leave sounds will no longer be played in voice channels."
        )

    @commands.command()
    async def setjoinsound(self, ctx, url: str = None):
        """
        Set the sound that plays when you join a voice channel.

        Providing no attachment or url will remove the current join sound.
        """
        if not url:
            attachments = ctx.message.attachments
            if not attachments:
                await self.config.user(ctx.author).join_sound.clear()
                return await ctx.send("I've reset your join sound.")
            url = attachments[0].url

        if not url.endswith((".mp3", ".wav")):
            await ctx.send("You need to provide a .mp3 or .wav file.")
            return

        async with self.session.get(url) as resp:
            if resp.status != 200:
                await ctx.send("That URL doesn't seem to work.")
                return

        await self.config.user(ctx.author).join_sound.set(url)
        await ctx.send(
            "I've set your sound that will be played upon you joining a voice channel."
        )

    @commands.command()
    async def setleavesound(self, ctx, url: str = None):
        """
        Set the sound that plays when you leave a voice channel.

        Providing no attachment or url will remove the current leave sound.
        """
        if not url:
            attachments = ctx.message.attachments
            if not attachments:
                await self.config.user(ctx.author).leave_sound.clear()
                return await ctx.send("I've reset your leave sound.")
            url = attachments[0].url

        if not url.endswith((".mp3", ".wav")):
            await ctx.send("You need to provide a .mp3 or .wav file.")
            return

        async with self.session.get(url) as resp:
            if resp.status != 200:
                await ctx.send("That URL doesn't seem to work.")
                return

        await self.config.user(ctx.author).join_sound.set(url)
        await ctx.send(
            "I've set your sound that will be played upon you leaving a voice channel."
        )
