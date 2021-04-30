from redbot.core import commands, Config
import discord
import random
import aiohttp
import datetime


class AutoAvatar(commands.Cog):
    """Chooses a random avatar to set from a preset list"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=696969696969494)
        default_global = {
            "avatars": ["https://avatars.githubusercontent.com/u/23690422?s=400&v=4"],
            "current_avatar": "",
            "current_channel": None,
            "submission_channel": None,
        }
        self.config.register_global(**default_global)

    async def change_avatar(self, ctx):
        all_avatars = await self.config.avatars()

        if all_avatars is None:
            return
        new_avatar = random.choice(all_avatars)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(new_avatar) as request:
                    avatar = await request.read()
            except aiohttp.InvalidURL:
                all_avatars.remove(new_avatar)
                await self.config.avatars.set(all_avatars)
                return
            except aiohttp.ClientError:
                all_avatars.remove(new_avatar)
                await self.config.avatars.set(all_avatars)
                return

        try:
            await self.bot.user.edit(avatar=avatar)
            await ctx.tick()
        except discord.HTTPException:
            return
        except discord.InvalidArgument:
            all_avatars.remove(new_avatar)
            await self.config.avatars.set(all_avatars)
            return

        await self.config.current_avatar.set(new_avatar)

        if await self.config.current_channel():
            channel = self.bot.get_channel(await self.config.current_channel())
            embed = discord.Embed(
                colour=await self.bot.get_embed_colour(channel),
                title="My Current Avatar",
                timestamp=datetime.datetime.utcnow(),
            )
            embed.set_image(url=new_avatar)
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                await self.config.current_channel.set(None)
                return

    @commands.group()
    @commands.is_owner()
    async def avatarchannel(self, ctx):
        """
        Commands to set the avatar channels.
        """
        pass

    @avatarchannel.command()
    async def current(self, ctx, channel: discord.TextChannel = None):
        """
        Sets the channel for the current avatar display.
        If no channel is provided, it will clear the set channel.
        """
        if channel is None:
            await self.config.current_channel.set(None)
            await ctx.send("I have cleared the channel.")
        else:
            await self.config.current_channel.set(channel.id)
            await ctx.tick()

    @avatarchannel.command()
    async def submissions(self, ctx, channel: discord.TextChannel = None):
        """
        Sets the channel for avatar submissions.
        If no channel is provided, it will clear the set channel.
        """
        if channel is None:
            await self.config.submission_channel.set(None)
            await ctx.send("I have cleared the channel.")
        else:
            await self.config.submission_channel.set(channel.id)
            await ctx.tick()

    @commands.command()
    @commands.is_owner()
    async def addavatar(self, ctx, link: str):
        """
        Adds an avatar link.
        """
        all_avatars = await self.config.avatars()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(link) as request:
                    avatar = await request.read()
            except aiohttp.InvalidURL:
                await ctx.send("That's not a valid link.")
                return
            except aiohttp.ClientError:
                await ctx.send("That's not a valid link.")
                return

        if link not in all_avatars:
            all_avatars.append(link)
            await self.config.avatars.set(all_avatars)
            await ctx.tick()
        else:
            await ctx.send(
                f"{link} was already in my list of avatars, did you mean to remove it?"
            )

    @commands.command()
    @commands.is_owner()
    async def removeavatar(self, ctx, link: str):
        """
        Removes an avatar link.
        """
        all_avatars = await self.config.avatars()

        if len(all_avatars) == 1:
            await ctx.send(
                "You can't remove this until you have more than one avatar remaining."
            )
            return

        if link in all_avatars:
            all_avatars.remove(link)
            await self.config.avatars.set(all_avatars)
            await ctx.tick()
        else:
            await ctx.send(
                f"{link} wasn't in my list of avatars, did you mean to add it?"
            )

    @commands.command()
    async def listavatars(self, ctx):
        """
        Lists all bot avatars.
        """
        all_avatars = await self.config.avatars()

        paginator = discord.ext.commands.help.Paginator()

        for obj in all_avatars:
            paginator.add_line(obj)

        for page in paginator.pages:
            await ctx.author.send(page)

    @commands.command()
    @commands.is_owner()
    async def newavatar(self, ctx):
        """
        Changes the bot avatar.
        """
        await self.change_avatar(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def currentavatar(self, ctx):
        """
        Displays the bot's current avatar.
        """
        avatar = await self.config.current_avatar()
        embed = discord.Embed(
            colour=await self.bot.get_embed_colour(ctx.channel),
            title="My Current Avatar",
        )
        embed.set_image(url=avatar)
        await ctx.send(embed=embed)

    @commands.command()
    async def submitavatar(self, ctx, link: str):
        """
        Submits a link for an avatar suggestion.
        """
        if await self.config.submission_channel() is None:
            await ctx.send("Ask the bot owner to set up the submissions channel!")
            return
        else:
            try:
                channel = self.bot.get_channel(await self.config.submission_channel())
                embed = discord.Embed(
                    colour=await self.bot.get_embed_colour(channel),
                    title="New Avatar Submission",
                    timestamp=datetime.datetime.utcnow(),
                )
                embed.set_image(url=link)
                await channel.send(embed=embed)
                await ctx.tick()
            except discord.HTTPException:
                await ctx.send("That doesn't look like a valid link!")
                return
