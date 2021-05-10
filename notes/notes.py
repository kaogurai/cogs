from redbot.core import commands, Config, modlog
import discord
import arrow


class Notes(commands.Cog):
    """Write notes on users for moderators to share."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=49494928388538483242032)
        default_user = {}
        self.config.register_global(**default_user)
        self.register_casetypes = self.bot.loop.create_task(self.register_casetypes())

    async def register_casetypes(self):
        casetypes = [
            {"name": "note", "default_setting": True, "image": "🗒", "case_str": "Note"},
            {
                "name": "note_burned",
                "default_setting": True,
                "image": "🔥",
                "case_str": "Note Burned",
            },
        ]
        try:
            await modlog.register_casetype(casetypes)
        except RuntimeError:
            pass

    async def write_note(self, ctx, user, moderator, reason):
        await modlog.create_case(
            guild=ctx.guild,
            bot=self.bot,
            created_at=arrow.utcnow(),
            action_type="note",
            user=user,
            moderator=moderator,
            reason=reason,
        )
        # TODO: add it to config

    async def burn_note(self, ctx, user, moderator, old_note_reason):
        await modlog.create_case(
            guild=ctx.guild,
            bot=self.bot,
            created_at=arrow.utcnow(),
            action_type="note_burned",
            user=user,
            moderator=moderator,
            reason=f"Note Removed: {old_note_reason}",
        )
        # TODO: remove it from config

    async def get_note(self, ctx, user, note: int):
        pass

    async def get_notes(self, ctx, user):
        pass

    @commands.command(aliases=["addnote"])
    @commands.guild()
    @commands.mod_or_permissions(ban_members=True)
    async def note(self, ctx, user: discord.Member, reason: str):
        """Create a note on a user."""
        if user == ctx.author:
            await ctx.send("You can't add a note to yourself.")
            return
        if user.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("You can't add a note to that user.")
            return
        if user == ctx.guild.owner:
            await ctx.send("You can't add a note to that user.")
            return
        if len(reason) > 500:
            await ctx.send("Notes can't be larger than 500 characters.")
            return
        # check if duplicate note exists
        await self.write_note(ctx, user, ctx.author, reason)
        await ctx.send(f"I have noted **{reason}** for **{user}**.")

    @commands.command(aliases=["deletenote", "removenote"])
    @commands.guild()
    @commands.mod_or_permissions(ban_members=True)
    async def delnote(self, ctx, user: discord.Member, note: int):
        """
        Remove a note from a user
        Use the index from `[p]notes <user>`
        """
        if user == ctx.author:
            await ctx.send("You can't remove note from yourself.")
            return
        if user.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("You can't remove a note from that user.")
            return
        if user == ctx.guild.owner:
            await ctx.send("You can't remove a note from that user.")
            return
        # check if note exists
        note = await self.get_note(note)
        await self.burn_note(ctx, user, ctx.author, note)
        await ctx.send(f"I have removed the note **{note}** from **{ctx.author}** ")

    @commands.command(aliases=["viewnotes", "listnotes"])
    @commands.guild()
    @commands.mod_or_permissions(ban_members=True)
    async def notes(self, ctx, user: discord.Member):
        """View notes on a user."""
        notes = await self.get_notes(self, ctx, user)
        await ctx.send(notes)  # make better
