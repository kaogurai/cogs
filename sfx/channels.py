import asyncio

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils.predicates import MessagePredicate

from .abc import MixinMeta


class TTSChannelMixin(MixinMeta):
    @commands.group()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def ttschannel(self, ctx):
        """
        Configures automatic TTS channels.
        """
        pass

    @ttschannel.command()
    async def add(self, ctx, channel: discord.TextChannel):
        """
        Adds a channel for automatic TTS.
        """
        channel_list = await self.config.guild(ctx.guild).channels()
        if channel.id not in channel_list:
            channel_list.append(channel.id)
            await self.config.guild(ctx.guild).channels.set(channel_list)
            await ctx.send(f"Okay, {channel.mention} will now be used as a TTS channel.")
        else:
            await ctx.send(
                f"{channel.mention} is already a TTS channel, did you mean use the `{ctx.clean_prefix}ttschannel remove` command?"
            )

    @ttschannel.command(aliases=["delete", "del"])
    async def remove(self, ctx, channel: discord.TextChannel):
        """
        Removes a channel for automatic TTS.
        """
        channel_list = await self.config.guild(ctx.guild).channels()
        if channel.id in channel_list:
            channel_list.remove(channel.id)
            await self.config.guild(ctx.guild).channels.set(channel_list)
            await ctx.send(f"Okay, {channel.mention} is no longer a TTS channel.")
        else:
            await ctx.send(
                f"{channel.mention} isn't a TTS channel, did you mean use the `{ctx.clean_prefix}ttschannel add` command?"
            )

    @ttschannel.command()
    async def clear(self, ctx):
        """
        Removes all the channels for automatic TTS.
        """
        channel_list = await self.config.guild(ctx.guild).channels()
        if not channel_list:
            await ctx.send("There's no channels in the config.")
        else:
            try:
                await ctx.send(
                    "Are you sure you want to clear all this server's TTS channels? Respond with yes or no."
                )
                predictate = MessagePredicate.yes_or_no(ctx, user=ctx.author)
                await ctx.bot.wait_for("message", check=predictate, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send(
                    "You never responded, please use the command again to clear all of this server's TTS channels."
                )
                return
            if predictate.result:
                await self.config.guild(ctx.guild).channels.clear()
                await ctx.send("Okay, I've cleared all TTS channels for this server.")
            else:
                await ctx.send("Okay, I won't clear any TTS channels.")

    @ttschannel.command()
    async def list(self, ctx):
        """
        Shows all the channels for automatic TTS.
        """
        channel_list = await self.config.guild(ctx.guild).channels()
        if not channel_list:
            await ctx.send("This server doesn't have any TTS channels set up.")
        else:
            text = "".join(f"<#{channel}> - {channel} \n" for channel in channel_list)
            pages = [p for p in pagify(text=text, delims="\n")]
            embeds = []
            for index, page in enumerate(pages):
                embed = discord.Embed(
                    title="Automatic TTS Channels",
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

    @commands.Cog.listener(name="on_message_without_command")
    async def ttschannels_message_listener(self, message: discord.Message):
        if (
            not message.guild
            or message.author.bot
            or not message.channel.permissions_for(message.guild.me).send_messages
            or not await self.bot.allowed_by_whitelist_blacklist(who=message.author)
            or await self.bot.cog_disabled_in_guild(self, message.guild)
            or message.author.id in self.autotts
            or not await self.can_tts(message)
        ):
            return

        channel_list = await self.config.guild(message.guild).channels()
        if message.channel.id not in channel_list:
            return

        if not message.author.voice or not message.author.voice.channel:
            await message.channel.send("You are not connected to a voice channel.")
            return

        if not message.author.voice.channel.permissions_for(message.author).speak:
            await message.channel.send(
                "You don't have permission to speak in this channel."
            )
            return

        await self.play_tts(
            message.author,
            message.author.voice.channel,
            message.channel,
            "ttschannel",
            message.clean_content,
        )
