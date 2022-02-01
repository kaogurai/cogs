import contextlib

import discord
from redbot.core import commands
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import pagify

from .abc import MixinMeta


class GuildManager(MixinMeta):
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """
        Leave guilds in the blacklist
        Leave guilds with less than 50 members
        Leave guilds with more than 50% bots
        Don't leave guilds in the whitelist
        """
        if not guild:
            return
        if guild.id in await self.config.whitelist():
            return
        if guild.id in await self.config.blacklist():
            await guild.leave()
            return
        botcount = len([x async for x in AsyncIter(guild.members) if x.bot])
        if guild.member_count < 50 or botcount / guild.member_count > 0.5:
            if hasattr(guild, "system_channel") and guild.system_channel:
                with contextlib.suppress(discord.Forbidden):
                    m = (
                        "I'm leaving this server because it doesn't meet my requirements.\n\n"
                        "Remember:\n"
                        "1. Your server needs more at least 50 members\n"
                        "2. You can't have more than 25% of your members be bots"
                    )
                    embed = discord.Embed(
                        title="Hey there!",
                        color=await self.bot.get_embed_colour(guild.system_channel),
                        description=m,
                    )
                    await guild.system_channel.send(embed=embed)
                        
            await guild.leave()
            return

        kao_channel = self.bot.get_channel(768663090337677312)
        joined = int(guild.created_at.timestamp())
        m = (
            f"• Guild Name: {guild.name}\n"
            f"• Guild ID: {guild.id}\n"
            f"• Member Count: {guild.member_count}\n"
            f"• Bot Count: {botcount}\n"
            f"• Guild Owner {guild.owner} ({guild.owner.id})\n"
            f"• Guild Creation: <t:{joined}> (<t:{joined}:R>)"
        )
        embed = discord.Embed(
            title="I joined a new server!",
            description=m,
            color=await self.bot.get_embed_colour(kao_channel),
        )
        await kao_channel.send(embed=embed)


    @commands.is_owner()
    @commands.group(aliases=["guildmgr"])
    async def guildmanager(self, ctx):
        """
        Manage bot guilds.
        """

    @guildmanager.command()
    async def whitelist(self, ctx, id: int = None):
        """
        Whitelist a guild or remove a guild from the whitelist.

        The whitelist will be listed if no guild is provided
        """
        list = await self.config.whitelist()
        if not id and not list:
            return await ctx.send("There are no guilds on the whitelist.")
        if not id:
            string = "Whitelisted Guilds:\n"
            for guild in list:
                guild_obj = self.bot.get_guild(guild)
                if guild_obj:
                    string += f"{guild_obj.name} ({guild_obj.id})\n"
                else:
                    string += f"{guild_obj.id}\n"
            for page in pagify(string, delims=["\n"]):
                await ctx.send(page)
            return
        if id in list:
            list.remove(id)
            await self.config.whitelist.set(list)
            await ctx.send(f"Removed {id} from the whitelist.")
            return
        list.append(id)
        await self.config.whitelist.set(list)
        await ctx.send(f"Added {id} to the whitelist.")

    @guildmanager.command()
    async def blacklist(self, ctx, id: int = None):
        """
        Blacklist a guild or remove a guild from the whitelist.

        The blacklist will be listed if no guild is provided
        """
        list = await self.config.blacklist()
        if not id and not list:
            return await ctx.send("There are no guilds on the blacklist.")
        if not id:
            string = "Blacklisted Guilds:\n"
            for guild in list:
                string += f"{guild}\n"
            for page in pagify(string, delims=["\n"]):
                await ctx.send(page)
            return
        if id in list:
            list.remove(id)
            await self.config.whitelist.set(list)
            await ctx.send(f"Removed {id} from the blacklist.")
            return
        list.append(id)
        await self.config.whitelist.set(list)
        await ctx.send(f"Added {id} to the blacklist.")
