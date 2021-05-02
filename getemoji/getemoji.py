from redbot.core import commands, Config, checks
import aiohttp
import discord


class GetEmoji(commands.Cog):
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.config = Config.get_conf(
            self, identifier=6574839238457654839284756548392384756
        )
        default_global = {"url": "http://localhost:6969/"}
        self.config.register_global(**default_global)

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

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
    async def apple(self, ctx, *, emoji: str):
        """get an image of a apple emoji"""
        await self.get_emoji(ctx, "apple", emoji)

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def google(self, ctx, *, emoji: str):
        """get an image of a google emoji"""
        await self.get_emoji(ctx, "google", emoji)

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def samsung(self, ctx, *, emoji: str):
        """get an image of a samsung emoji"""
        await self.get_emoji(ctx, "samsung", emoji)

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def microsoft(self, ctx, *, emoji: str):
        """get an image of a microsoft emoji"""
        await self.get_emoji(ctx, "microsoft", emoji)

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def whatsapp(self, ctx, *, emoji: str):
        """get an image of a whatsapp emoji"""
        await self.get_emoji(ctx, "whatsapp", emoji)

    @getemoji.command(aliases=["discord"])
    @commands.bot_has_permissions(embed_links=True)
    async def twitter(self, ctx, *, emoji: str):
        """get an image of a twitter/discord emoji"""
        await self.get_emoji(ctx, "twitter", emoji)

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def facebook(self, ctx, *, emoji: str):
        """get an image of a facebook emoji"""
        await self.get_emoji(ctx, "facebook", emoji)

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def joypixels(self, ctx, *, emoji: str):
        """get an image of a joypixels emoji"""
        await self.get_emoji(ctx, "joypixels", emoji)

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def openmoji(self, ctx, *, emoji: str):
        """get an image of a openmoji emoji"""
        await self.get_emoji(ctx, "openmoji", emoji)

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def emojidex(self, ctx, *, emoji: str):
        """get an image of a emojidex emoji"""
        await self.get_emoji(ctx, "emojidex", emoji)

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def lg(self, ctx, *, emoji: str):
        """get an image of a lg emoji"""
        await self.get_emoji(ctx, "lg", emoji)

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def htc(self, ctx, *, emoji: str):
        """get an image of a htc emoji"""
        await self.get_emoji(ctx, "htc", emoji)

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def softbank(self, ctx, *, emoji: str):
        """get an image of a softbank emoji"""
        await self.get_emoji(ctx, "softbank", emoji)

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def docomo(self, ctx, *, emoji: str):
        """get an image of a docomo emoji"""
        await self.get_emoji(ctx, "docomo", emoji)

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def mozilla(self, ctx, *, emoji: str):
        """get an image of a mozilla emoji"""
        await self.get_emoji(ctx, "mozille", emoji)

    @getemoji.command()
    @commands.bot_has_permissions(embed_links=True)
    async def messenger(self, ctx, *, emoji: str):
        """get an image of a messenger emoji"""
        await self.get_emoji(ctx, "messenger", emoji)

    async def get_emoji(self, ctx, vendor, emoji):
        await ctx.trigger_typing()
        url = await self.config.url()
        try:
            async with self.session.get(
                url + f"emoji/image/{vendor}/" + emoji
            ) as request:
                if request.status == 404:
                    await ctx.send("Sorry, I couldn't find that emoji from my API.")
                    return
                response = await request.json()
                embed = discord.Embed(color=await ctx.embed_colour())
                embed.set_image(url=response["url"])
                await ctx.send(embed=embed)
        except:
            await ctx.send(
                "Uh oh, an error occured. Make sure the API is listening on the correct port."
            )
