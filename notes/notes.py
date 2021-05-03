from redbot.core import commands, Config, modlog
import discord
import arrow


class Notes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=49494928388538483242032)
        default_user = {}
        self.config.register_global(**default_user)

    async def write_note(self, ctx, user, moderator, reason):
        try:
            await modlog.register_casetype(
                name="Note",
                default_setting=True,
                image="🗒",
                case_str="Note",
            )
        except RuntimeError:
            pass

        await modlog.create_case(
            guild=ctx.guild,
            bot=self.bot,
            created_at=arrow.utcnow(),
            action_type="Note",
            user=user,
            moderator=moderator,
            reason=reason,
        )

        # TODO: add it to config

    async def burn_note(self, ctx, user, moderator, reason):
        try:
            await modlog.register_casetype(
                name="Note Burned",
                default_setting=True,
                image="🔥",
                case_str="Note Burned",
            )
        except RuntimeError:
            pass

        await modlog.create_case(
            guild=ctx.guild,
            bot=self.bot,
            created_at=arrow.utcnow(),
            action_type="Note Burned",
            user=user,
            moderator=moderator,
            reason=reason,
        )

        # TODO: remove it from config

    @commands.command(aliases=["addnote"])
    @commands.mod_or_permissions(ban_members=True)
    async def note(self, ctx, user: discord.Member, reason: str):
        await self.write_note(ctx, user, ctx.author, reason)

    @commands.command(aliases=["deletenote", "removenote"])
    @commands.mod_or_permissions(ban_members=True)
    async def delnote(self, ctx, user: discord.Member, reason: str, note: int):
        await self.burn_note(ctx, user, ctx.author, reason, note)

    @commands.command(aliases=["viewnotes", "listnotes"])
    @commands.mod_or_permissions(ban_members=True)
    async def notes(self, ctx, user: discord.Member):
        pass

    @commands.command()
    @commands.mod_or_permissions(ban_members=True)
    async def clearnotes(self, ctx, user: discord.Member):
        pass
