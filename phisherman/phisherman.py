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
            enabled=False, suspicious_ban=False, malicious_ban=True
        )

    @commands.command(aliases=["checkforphish", "checkscam", "checkforscam"])
    @commands.bot_has_permissions(embed_links=True)
    async def checkphish(self, ctx, url: str):
        """
        Check if a url is a phishing scam.
        """

    @commands.group()
    @commands.guild_only()
    @commands.is_admin_or_permissions(manage_guild=True)
    async def phisherman(self, ctx):
        """
        Settings to set up phisherman.
        """
        pass
