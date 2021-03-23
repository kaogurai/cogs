from redbot.core import commands, Config, checks
import aiohttp 
import discord

class GetEmoji(commands.Cog):
    def __init__(self):
        self.config = Config.get_conf(self, identifier=6574839238457654839284756548392384756)
        default_global = {"url": "http://localhost:6969/" }
        self.config.register_global(**default_global)

    @commands.command()
    @commands.is_owner()
    async def emojiapiurl(self, ctx, url: str):
        """set the url for the emoji api server"""
        await self.config.url.set(url)
        await ctx.tick()

    @commands.group()
    async def getemoji(self, ctx):
        """get custom emojis from different providers!"""
        pass

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def apple(self, ctx, emoji: str):
        """get an image of a apple emoji"""
        await ctx.trigger_typing()
        url = await self.config.url()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url + 'emoji/image/apple/' + emoji) as request:
                    if request.status == 404:
                        return await ctx.send("Sorry, I couldn't find that emoji from my API.")
                    response = await request.json()
                    embed = discord.Embed(color = await ctx.embed_colour())
                    embed.set_image(url = response['url'])
                    await ctx.send(embed = embed)
        except aiohttp.ClientConnectionError:
            await ctx.send("Sorry, the API isn't set up correctly.")

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def google(self, ctx, emoji: str):
        """get an image of a google emoji"""
        await ctx.trigger_typing()
        url = await self.config.url()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url + 'emoji/image/google/' + emoji) as request:
                    if request.status == 404:
                        return await ctx.send("Sorry, I couldn't find that emoji from my API.")
                    response = await request.json()
                    embed = discord.Embed(color = await ctx.embed_colour())
                    embed.set_image(url = response['url'])
                    await ctx.send(embed = embed)
        except aiohttp.ClientConnectionError:
            await ctx.send("Sorry, the API isn't set up correctly.")

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def samsung(self, ctx, emoji: str):
        """get an image of a samsung emoji"""
        await ctx.trigger_typing()
        url = await self.config.url()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url + 'emoji/image/samsung/' + emoji) as request:
                    if request.status == 404:
                        return await ctx.send("Sorry, I couldn't find that emoji from my API.")
                    response = await request.json()
                    embed = discord.Embed(color = await ctx.embed_colour())
                    embed.set_image(url = response['url'])
                    await ctx.send(embed = embed)
        except aiohttp.ClientConnectionError:
            await ctx.send("Sorry, the API isn't set up correctly.")

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def microsoft(self, ctx, emoji: str):
        """get an image of a microsoft emoji"""
        await ctx.trigger_typing()
        url = await self.config.url()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url + 'emoji/image/microsoft/' + emoji) as request:
                    if request.status == 404:
                        return await ctx.send("Sorry, I couldn't find that emoji from my API.")
                    response = await request.json()
                    embed = discord.Embed(color = await ctx.embed_colour())
                    embed.set_image(url = response['url'])
                    await ctx.send(embed = embed)
        except aiohttp.ClientConnectionError:
            await ctx.send("Sorry, the API isn't set up correctly.")

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def whatsapp(self, ctx, emoji: str):
        """get an image of a whatsapp emoji"""
        await ctx.trigger_typing()
        url = await self.config.url()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url + 'emoji/image/whatsapp/' + emoji) as request:
                    if request.status == 404:
                        return await ctx.send("Sorry, I couldn't find that emoji from my API.")
                    response = await request.json()
                    embed = discord.Embed(color = await ctx.embed_colour())
                    embed.set_image(url = response['url'])
                    await ctx.send(embed = embed)
        except aiohttp.ClientConnectionError:
            await ctx.send("Sorry, the API isn't set up correctly.")

    @getemoji.command(aliases=["discord"])
    @commands.bot_has_permissions(embed_links=True)
    async def twitter(self, ctx, emoji: str):
        """get an image of a twitter/discord emoji"""
        await ctx.trigger_typing()
        url = await self.config.url()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url + 'emoji/image/twitter/' + emoji) as request:
                    if request.status == 404:
                        return await ctx.send("Sorry, I couldn't find that emoji from my API.")
                    response = await request.json()
                    embed = discord.Embed(color = await ctx.embed_colour())
                    embed.set_image(url = response['url'])
                    await ctx.send(embed = embed)
        except aiohttp.ClientConnectionError:
            await ctx.send("Sorry, the API isn't set up correctly.")

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def facebook(self, ctx, emoji: str):
        """get an image of a facebook emoji"""
        await ctx.trigger_typing()
        url = await self.config.url()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url + 'emoji/image/facebook/' + emoji) as request:
                    if request.status == 404:
                        return await ctx.send("Sorry, I couldn't find that emoji from my API.")
                    response = await request.json()
                    embed = discord.Embed(color = await ctx.embed_colour())
                    embed.set_image(url = response['url'])
                    await ctx.send(embed = embed)
        except aiohttp.ClientConnectionError:
            await ctx.send("Sorry, the API isn't set up correctly.")

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def joypixels(self, ctx, emoji: str):
        """get an image of a joypixels emoji"""
        await ctx.trigger_typing()
        url = await self.config.url()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url + 'emoji/image/joypixels/' + emoji) as request:
                    if request.status == 404:
                        return await ctx.send("Sorry, I couldn't find that emoji from my API.")
                    response = await request.json()
                    embed = discord.Embed(color = await ctx.embed_colour())
                    embed.set_image(url = response['url'])
                    await ctx.send(embed = embed)
        except aiohttp.ClientConnectionError:
            await ctx.send("Sorry, the API isn't set up correctly.")

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def openmoji(self, ctx, emoji: str):
        """get an image of a openmoji emoji"""
        await ctx.trigger_typing()
        url = await self.config.url()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url + 'emoji/image/openmoji/' + emoji) as request:
                    if request.status == 404:
                        return await ctx.send("Sorry, I couldn't find that emoji from my API.")
                    response = await request.json()
                    embed = discord.Embed(color = await ctx.embed_colour())
                    embed.set_image(url = response['url'])
                    await ctx.send(embed = embed)
        except aiohttp.ClientConnectionError:
            await ctx.send("Sorry, the API isn't set up correctly.")

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def emojidex(self, ctx, emoji: str):
        """get an image of a emojidex emoji"""
        await ctx.trigger_typing()
        url = await self.config.url()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url + 'emoji/image/emojidex/' + emoji) as request:
                    if request.status == 404:
                        return await ctx.send("Sorry, I couldn't find that emoji from my API.")
                    response = await request.json()
                    embed = discord.Embed(color = await ctx.embed_colour())
                    embed.set_image(url = response['url'])
                    await ctx.send(embed = embed)
        except aiohttp.ClientConnectionError:
            await ctx.send("Sorry, the API isn't set up correctly.")

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def lg(self, ctx, emoji: str):
        """get an image of a lg emoji"""
        await ctx.trigger_typing()
        url = await self.config.url()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url + 'emoji/image/lg/' + emoji) as request:
                    if request.status == 404:
                        return await ctx.send("Sorry, I couldn't find that emoji from my API.")
                    response = await request.json()
                    embed = discord.Embed(color = await ctx.embed_colour())
                    embed.set_image(url = response['url'])
                    await ctx.send(embed = embed)
        except aiohttp.ClientConnectionError:
            await ctx.send("Sorry, the API isn't set up correctly.")

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def htc(self, ctx, emoji: str):
        """get an image of a htc emoji"""
        await ctx.trigger_typing()
        url = await self.config.url()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url + 'emoji/image/htc/' + emoji) as request:
                    if request.status == 404:
                        return await ctx.send("Sorry, I couldn't find that emoji from my API.")
                    response = await request.json()
                    embed = discord.Embed(color = await ctx.embed_colour())
                    embed.set_image(url = response['url'])
                    await ctx.send(embed = embed)
        except aiohttp.ClientConnectionError:
            await ctx.send("Sorry, the API isn't set up correctly.")

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def softbank(self, ctx, emoji: str):
        """get an image of a softbank emoji"""
        await ctx.trigger_typing()
        url = await self.config.url()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url + 'emoji/image/softbank/' + emoji) as request:
                    if request.status == 404:
                        return await ctx.send("Sorry, I couldn't find that emoji from my API.")
                    response = await request.json()
                    embed = discord.Embed(color = await ctx.embed_colour())
                    embed.set_image(url = response['url'])
                    await ctx.send(embed = embed)
        except aiohttp.ClientConnectionError:
            await ctx.send("Sorry, the API isn't set up correctly.")

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def docomo(self, ctx, emoji: str):
        """get an image of a docomo emoji"""
        await ctx.trigger_typing()
        url = await self.config.url()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url + 'emoji/image/docomo/' + emoji) as request:
                    if request.status == 404:
                        return await ctx.send("Sorry, I couldn't find that emoji from my API.")
                    response = await request.json()
                    embed = discord.Embed(color = await ctx.embed_colour())
                    embed.set_image(url = response['url'])
                    await ctx.send(embed = embed)
        except aiohttp.ClientConnectionError:
            await ctx.send("Sorry, the API isn't set up correctly.")

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def mozilla(self, ctx, emoji: str):
        """get an image of a mozilla emoji"""
        await ctx.trigger_typing()
        url = await self.config.url()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url + 'emoji/image/mozilla/' + emoji) as request:
                    if request.status == 404:
                        return await ctx.send("Sorry, I couldn't find that emoji from my API.")
                    response = await request.json()
                    embed = discord.Embed(color = await ctx.embed_colour())
                    embed.set_image(url = response['url'])
                    await ctx.send(embed = embed)
        except aiohttp.ClientConnectionError:
            await ctx.send("Sorry, the API isn't set up correctly.")

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def messenger(self, ctx, emoji: str):
        """get an image of a messenger emoji"""
        await ctx.trigger_typing()
        url = await self.config.url()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url + 'emoji/image/messenger/' + emoji) as request:
                    if request.status == 404:
                        return await ctx.send("Sorry, I couldn't find that emoji from my API.")
                    response = await request.json()
                    embed = discord.Embed(color = await ctx.embed_colour())
                    embed.set_image(url = response['url'])
                    await ctx.send(embed = embed)
        except aiohttp.ClientConnectionError:
            await ctx.send("Sorry, the API isn't set up correctly.")
