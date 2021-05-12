from redbot.core import commands, Config
import discord
import random
import aiohttp
import datetime


class AutoAvatar(commands.Cog):
    """Chooses a random avatar to set from a preset list"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.config = Config.get_conf(self, identifier=696969696969494)
        default_global = {"avatars": [], "current_avatar": "", "current_channel": None}
        self.config.register_global(**default_global)

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def change_avatar(self, ctx):
        all_avatars = await self.config.avatars()

        if not all_avatars:
            await ctx.send("You haven't added any avatars yet.")
            return

        new_avatar = random.choice(all_avatars)

        try:
            async with self.session.get(new_avatar) as request:
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
                return

    @commands.command()
    @commands.is_owner()
    async def avatarchannel(self, ctx, channel: discord.TextChannel = None):
        """
        Sets the channel for the current avatar.
        If no channel is provided, it will clear the set channel.
        """
        if channel is None:
            await self.config.current_channel.set(None)
            await ctx.send("I have cleared the channel.")
        else:
            await self.config.current_channel.set(channel.id)
            await ctx.tick()

    @commands.command()
    @commands.is_owner()
    async def addavatar(self, ctx, link: str):
        """
        Adds an avatar link.
        """
        all_avatars = await self.config.avatars()

        try:
            await self.session.get(link)
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

        if not all_avatars:
            await ctx.send("I do not have any avatars saved.")
            return

        paginator = discord.ext.commands.help.Paginator()

        for obj in all_avatars:
            paginator.add_line(obj)

        for page in paginator.pages:
            try:
                await ctx.author.send(page)
            except:
                await ctx.send("I can't DM you.")
                break

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
