from redbot.core import commands, Config, modlog
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
import discord
import arrow


class Notes(commands.Cog):
    """Write notes on users for moderators to share."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=49494928388538483242032)
        default_member = {"notes": []}
        self.config.register_member(**default_member)
        self.register_casetypes = self.bot.loop.create_task(self.register_casetypes())

    async def register_casetypes(self):
        try:
            await modlog.register_casetype(
                name="note",
                default_setting=True,
                image="🗒",
                case_str="Note",
            )
        except RuntimeError:
            pass # this means it's already been registered
        try:
            await modlog.register_casetype(
                name="note_burned",
                default_setting=True,
                image="🔥",
                case_str="Note Burned",
            )
        except RuntimeError:
            pass # this means it's already been registered

    async def write_note(self, ctx, user, moderator, reason: str):
        """Create a modlog case and add it to the user's config."""
        await modlog.create_case(
            guild=ctx.guild,
            bot=self.bot,
            created_at=arrow.utcnow(),
            action_type="note",
            user=user,
            moderator=moderator,
            reason=reason,
        )
        user_notes = await self.config.member(user).notes()
        user_notes.append(
            {
                'note': reason,
                'author': moderator.id,
                'message': ctx.message.id
            }
        )
        await self.config.member(user).notes.set(user_notes)

    async def burn_note(self, ctx, user, moderator, notes, note):
        """Create a modlog case and remove it from the user's config."""
        old_note = notes[note]
        old_note_text = old_note['note']
        await modlog.create_case(
            guild=ctx.guild,
            bot=self.bot,
            created_at=arrow.utcnow(),
            action_type="note_burned",
            user=user,
            moderator=moderator,
            reason=f"Note Removed: {old_note_text}",
        )
        notes.remove(old_note)
        await self.config.member(user).notes.set(notes)
        return old_note_text


    @commands.guild_only()
    @commands.command(aliases=["addnote"])
    @commands.mod_or_permissions(ban_members=True)
    async def note(self, ctx, user: discord.Member, *, reason: str):
        """Add a note to a user."""
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
        await self.write_note(ctx, user, ctx.author, reason)
        await ctx.send(f"I have noted **{reason}** for **{user}**.")

    @commands.command(aliases=["deletenote", "removenote"])
    @commands.guild_only()
    @commands.mod_or_permissions(ban_members=True)
    async def delnote(self, ctx, user: discord.Member, note: int):
        """
        Remove a note from a user.
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
        notes = await self.config.member(user).notes()
        if note <= len(notes) and note >= 1:
            old_note_text = await self.burn_note(ctx, user, ctx.author, notes, note-1)
            await ctx.send(f"I have removed the note **{old_note_text}** from **{user}**.")
        else:
            await ctx.send("That note doesn't seem to exist.")

    @commands.command(aliases=["viewnotes", "listnotes"])
    @commands.guild_only()
    @commands.mod_or_permissions(ban_members=True)
    async def notes(self, ctx, user: discord.Member):
        """View a user's notes."""
        notes = await self.config.member(user).notes()
        if notes is None:
            await ctx.send("That user has no notes.")
            return
        embeds = []
        for index, page in enumerate(notes):
            author = self.bot.get_user(page['author'])
            embed = discord.Embed(
                color=await ctx.embed_color(),
                title=f"Note by {author}",
                description=page['note'],
            )
            if len(notes) != 1:
                embed.set_footer(text=f"Note {index + 1}/{len(notes)}")
            embeds.append(embed)
        if len(notes) != 1:
            await menu(ctx, embeds, controls=DEFAULT_CONTROLS, timeout=120)
        else:
            await ctx.send(embed=embeds[0])