import aiohttp
import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu


class NTFYStatus(commands.Cog):
    """
    Send push notifications using ntfy.sh when a bot goes offline.
    """

    __version__ = "1.0.3"

    def __init__(self, bot: Red):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.config = Config.get_conf(self, identifier=5453)
        self.config.register_user(bots=[])
        self.cache = {}
        self.bot.loop.create_task(self.load_cache())

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx: Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def load_cache(self) -> None:
        self.cache = await self.config.all_users()

    async def send_notification(self, channel: str, message: str, urgent: bool) -> None:
        headers = {"Title": "Bot status has changed"}
        if urgent:
            headers["Priority"] = "max"
            headers["Tags"] = "rotating_light"
        else:
            headers["Tags"] = "tada"
        await self.session.post(
            f"https://ntfy.sh/{channel}",
            data=message,
            headers=headers,
        )

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Online -> Offline
        if (
            before.status != after.status
            and str(after.status) == "offline"
            and str(before.status)
            in [
                "online", "idle", "dnd"
            ]
        ):
            for user in self.cache:
                user_config = self.cache.get(user, {"bots": []})
                for bot in user_config["bots"]:
                    if bot["id"] == before.id:
                        await self.send_notification(
                            bot["channel"],
                            f"Discord Bot {after.name} ({after.id}) is now offline.",
                            True,
                        )

        # Offline -> Online
        if (
            before.status != after.status
            and str(after.status)
            in [
                "online", "idle", "dnd"
            ]
            and str(before.status)  == "offline"
        ):
            for user in self.cache:
                user_config = self.cache.get(user, {"bots": []})
                for bot in user_config["bots"]:
                    if bot["id"] == before.id:
                        await self.send_notification(
                            bot["channel"],
                            f"Discord Bot {after.name} ({after.id}) is back online.",
                            False,
                        )

    @commands.group()
    async def ntfystatus(self, ctx: Context):
        """
        Commands to configure the bots you get notifications for.
        """

    @ntfystatus.command(name="add")
    async def ntfystatus_add(self, ctx: Context, channel: str, *, bot: discord.User):
        """
        Add a bot to the list of bots you get notifications for.

        Parameters:
            channel: str -  The channel you want to send the notification to. This is the ntfy.sh channel ID, not a discord channel.
            bot: discord.User - The bot you want to get notifications for.
        """
        bots = await self.config.user(ctx.author).bots()
        if bot.id in [x["id"] for x in bots]:
            await ctx.send(f"You're already getting notifications for that bot.")
            return

        if not bot.bot:
            await ctx.send("Creep.")
            return

        if not self.bot.get_user(bot.id):
            await ctx.send(
                "I don't share any servers with that bot. Please add it to one of my servers and try again."
            )
            return

        bots.append({"id": bot.id, "channel": channel})
        await self.config.user(ctx.author).bots.set(bots)

        self.cache[ctx.author.id] = bots

        await ctx.send("You will now get notifications for that bot.")

        if ctx.guild and ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.message.delete()

    @ntfystatus.command(name="remove")
    async def ntfystatus_remove(self, ctx: Context, bot: discord.User):
        """
        Stop getting notifications for a bot.

        Parameters:
            bot: discord.User - The bot you want to stop getting notifications for.
        """
        bots = await self.config.user(ctx.author).bots()
        if bot.id not in [x["id"] for x in bots]:
            await ctx.send(f"You're not getting notifications for that bot.")
            return

        bots.remove([x for x in bots if x["id"] == bot.id][0])
        await self.config.user(ctx.author).bots.set(bots)

        self.cache[ctx.author.id] = bots

        await ctx.send("You will no longer get notifications for that bot.")

    @ntfystatus.command(name="list")
    async def ntfystatus_list(self, ctx: Context):
        """
        List the bots you get notifications for.

        If the command is run in DMs, it will show the channel it posts to.
        """
        bots = self.cache.get(ctx.author.id, [])
        if not bots:
            await ctx.send("You don't have any bots set up.")
            return

        msg = ""
        if ctx.guild:
            msg = ",".join([f"<@{bot['id']}>" for bot in bots])
        else:
            for bot in bots:
                msg += f"<@{bot['id']}> - `{bot['channel']}`\n"

        pages = [p for p in pagify(text=msg, delims="\n")]
        embeds = []
        for index, page in enumerate(pages):
            embed = discord.Embed(
                title="Bots you get notifications for:",
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
