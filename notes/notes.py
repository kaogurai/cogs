from redbot.core import commands, Config, modlog
import discord
import arrow


class Notes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=49494928388538483242032)
        default_user = {}
        self.config.register_global(**default_user)

    async def add_note(self, ctx, member, mod, reason):
        # create the modlog type if it hasn't already been created
        try:
            await modlog.register_casetype(
                name="Note",
                default_setting=True,
                image="\N{SPIRAL NOTE PAD}\N{VARIATION SELECTOR-16}",
                case_str="Note",
            )
        except RuntimeError:
            pass

        # create the modlog case
        await modlog.create_case(
            guild=ctx.guild,
            bot=self.bot,
            created_at=arrow.utcnow(),
            action_type="Note",
            user=member,
            moderator=mod,
            reason=reason,
        )

        # TODO: add it to config

    async def remove_note(self, ctx, member, mod, reason):
        # create the modlog type if it hasn't already been created
        try:
            await modlog.register_casetype(
                name="Note Burned",
                default_setting=True,
                image="🔥",  # fix
                case_str="Note Burned",
            )
        except RuntimeError:
            pass

        # create the modlog case
        await modlog.create_case(
            guild=ctx.guild,
            bot=self.bot,
            created_at=arrow.utcnow(),
            action_type="Note Burned",
            user=member,
            moderator=mod,
            reason=reason,
        )

        # TODO: remove it from config

    @commands.command(aliases=["addnote"])
    @commands.mod_or_permissions(ban_members=True)
    async def note(self, ctx, user: discord.Member):
        pass

    @commands.command(aliases=["viewnotes", "listnotes"])
    @commands.mod_or_permissions(ban_members=True)
    async def notes(self, ctx, user: discord.Member):
        pass

    @commands.command()
    @commands.mod_or_permissions(ban_members=True)
    async def clearnotes(self, ctx, user: discord.Member):
        pass

    @commands.command(aliases=["deletenote", "removenote"])
    @commands.mod_or_permissions(ban_members=True)
    async def delnote(self, ctx, user: discord.Member):
        pass
