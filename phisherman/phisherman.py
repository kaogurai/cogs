from redbot.core import Config, commands


class PhisherMan(commands.Cog):
    """
    Protects users against phishing attacks.
    """

    __version__ = "1.0.0"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=73835)
        self.config.register_guild(
            enabled=False, safe="ignore", suspicious="delete", malicious="ban"
        )
        self.bot.loop.create_task(self.set_token())

    async def set_token(self):
        token = await self.bot.get_shared_api_tokens("phisherman")
        self.key = token.get("key")

    @commands.Cog.listener()
    async def on_red_api_tokens_update(self, service_name, api_tokens):
        if service_name == "phisherman":
            self.key = api_tokens.get("key")

    @commands.command(aliases=["checkforphish", "checkscam", "checkforscam"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def checkphish(self, ctx, url: str):
        """
        Check if a url is a phishing scam.
        """

    @commands.group()
    @commands.guild_only()
    @commands.is_admin_or_permissions(manage_guild=True)
    async def phisherman(self, ctx):
        """
        Settings to set the phisherman integration.
        """
