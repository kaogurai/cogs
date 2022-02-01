from redbot.core import commands

from .abc import MixinMeta


class ProxyMixin(MixinMeta):
    @commands.command(hidden=True)
    @commands.is_owner()
    async def ttsproxy(self, ctx, url: str = None):
        """
        Set the url to the 6p proxy.

        This is not needed, but you can set it up here if you want:
        https://github.com/aleclol/6p
        """

        if url is None:
            await self.config.proxy_url.clear()
            await ctx.send("I will no longer use a proxy for TTS.")
            return

        await self.config.proxy_url.set(url)
        await ctx.send("I've set the proxy URL.")
