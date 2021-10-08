import datetime
import random
from io import BytesIO

import aiohttp
import discord
from bs4 import BeautifulSoup
from PIL import Image
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import pagify


class AutoAvatar(commands.Cog):
    """
    Chooses a random avatar to set from a preset list or can scrape we heart it.
    """

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.config = Config.get_conf(self, identifier=696969696969494)
        default_global = {
            "avatars": [],
            "current_avatar": None,
            "current_channel": None,
            "auto_color": False,
            "weheartit": False,
        }
        self.config.register_global(**default_global)

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    def get_color(self, avatar):
        try:
            img = Image.open(BytesIO(avatar))
        except Exception:
            return
        resized = img.resize((1, 1))
        color = resized.getpixel((0, 0))
        int = (color[0] << 16) + (color[1] << 8) + color[2]
        return int

    async def get_we_heart_it_image(self):
        current_avatar = await self.config.current_avatar()
        async with self.session.get("https://weheartit.com") as request:
            if request.status == 200:
                page = await request.text()
                soup = BeautifulSoup(page, "html.parser")
                divs = soup.select("div.entry.grid-item")
                links = []
                for div in divs:
                    link = div.select("img.entry-thumbnail")[0].attrs["src"]
                    better_quality_link = link.replace("superthumb", "original")
                    links.append(better_quality_link)
                link = None
                while True:
                    link = random.choice(links)
                    if link != current_avatar:
                        return link

    async def change_avatar(self, ctx):
        all_avatars = await self.config.avatars()
        auto_color = await self.config.auto_color()
        we_heart_it = await self.config.weheartit()

        if we_heart_it:
            new_avatar = await self.get_we_heart_it_image()
            if not new_avatar:
                await ctx.send("There seems to be issues with weheartit currently.")
                return
        else:
            if not all_avatars:
                await ctx.send("You haven't added any avatars yet.")
                return

            new_avatar = random.choice(all_avatars)

        async with self.session.get(new_avatar) as request:
            if request.status == 200:
                avatar = await request.read()
            else:
                if we_heart_it:
                    all_avatars.remove(new_avatar)
                    await self.config.avatars.set(all_avatars)
                return

        if auto_color:
            result = await self.bot.loop.run_in_executor(None, self.get_color, avatar)
            if result:
                ctx.bot._color = result
                await ctx.bot._config.color.set(result)

        try:
            await self.bot.user.edit(avatar=avatar)
        except discord.HTTPException:
            return
        except discord.InvalidArgument:
            all_avatars.remove(new_avatar)
            await self.config.avatars.set(all_avatars)
            return

        await ctx.tick()
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

    @commands.group()
    async def autoavatar(self, ctx):
        pass

    @autoavatar.command()
    @commands.is_owner()
    async def settings(self, ctx):
        """
        Show AutoAvatar settings.
        """
        id = await self.config.current_channel()
        embed = discord.Embed(
            title="AutoAvatar Settings", colour=await ctx.embed_color()
        )
        embed.add_field(
            name="Auto Color",
            value="Enabled" if await self.config.auto_color() else "Disabled",
        )
        embed.add_field(
            name="We Heart It",
            value="Enabled" if await self.config.weheartit() else "Disabled",
        )
        embed.add_field(
            name="Current Avatar",
            value=f"[Click Here]({await self.config.current_avatar()})",
        )
        embed.add_field(name="Avatars Added", value=len(await self.config.avatars()))
        embed.add_field(name="Current Channel", value=f"<#{id}>" if id else "Disabled")
        await ctx.send(embed=embed)

    @autoavatar.command()
    @commands.is_owner()
    async def channel(self, ctx, channel: discord.TextChannel = None):
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

    @autoavatar.command()
    @commands.is_owner()
    async def add(self, ctx, *links: str):
        """
        Adds avatar links.
        """
        all_avatars = await self.config.avatars()

        for link in links:
            try:
                async with self.session.get(link) as r:
                    if r.status != 200:
                        await ctx.send(f"{link[:1000]} is not a valid link.")
                        continue
            except Exception:
                await ctx.send(f"{link[:1000]} is not a valid link.")
                continue

            if link not in all_avatars:
                all_avatars.append(link)
            else:
                await ctx.send(
                    f"{link:1000} was already in my list of avatars, did you mean to remove it?"
                )
        await self.config.avatars.set(all_avatars)
        await ctx.tick()

    @autoavatar.command()
    @commands.is_owner()
    async def remove(self, ctx, *links: str):
        """
        Removes an avatar link.
        """
        all_avatars = await self.config.avatars()

        for link in links:
            if link in all_avatars:
                all_avatars.remove(link)
            else:
                await ctx.send(
                    f"{link} wasn't in my list of avatars, did you mean to add it?"
                )
        await self.config.avatars.set(all_avatars)
        await ctx.tick()

    @autoavatar.command()
    async def list(self, ctx):
        """
        Lists all bot avatars.
        """
        all_avatars = await self.config.avatars()

        if not all_avatars:
            await ctx.send("I do not have any avatars saved.")
            return

        origin = ""

        for link in all_avatars:
            toappend = "<" + link + ">" + "\n"
            origin += toappend

        pages = [p for p in pagify(text=origin, delims="\n")]

        for page in pages:
            try:
                await ctx.author.send(page)
            except:
                await ctx.send("I can't DM you.")
                return
        await ctx.tick()

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

    @autoavatar.command()
    @commands.is_owner()
    async def color(self, ctx):
        """
        Toggle if the embed color is based on the avatar's color.
        """
        auto_color = await self.config.auto_color()
        await self.config.auto_color.set(not auto_color)
        await ctx.send(
            f"The embed color is now {'automatic' if not auto_color else 'manual'}."
        )

    @autoavatar.command()
    @commands.is_owner()
    async def weheartit(self, ctx):
        """
        Toggle if the bot uses weheartit for new avatars.
        """
        weheartit = await self.config.weheartit()
        new = not weheartit
        if new:
            await self.config.weheartit.set(True)
            await ctx.send("I will now use weheartit for new avatars.")
        else:
            await self.config.weheartit.set(False)
            await ctx.send("I will no longer use weheartit for new avatars.")
