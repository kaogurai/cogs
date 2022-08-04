import asyncio
import contextlib
from typing import Optional, Union

import aiohttp
import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu, start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate


class ChatBot(commands.Cog):
    """
    Cog that that allows users to chat with a chatbot.
    """

    __version__ = "1.0.0"

    def __init__(self, bot: Red):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.config = Config.get_conf(self, identifier=6574837465473)
        self.config.register_guild(channels=[], mention=True, reply=True)
        self.bot.loop.create_task(self.initialize())

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx: Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    @commands.Cog.listener()
    async def on_red_api_tokens_update(self, service_name: str, api_tokens: dict):
        if service_name == "brainshop":
            self.brain_id = api_tokens.get("brain_id")
            self.api_key = api_tokens.get("api_key")

    async def initialize(self) -> None:
        brainshop = await self.bot.get_shared_api_tokens("brainshop")
        self.brain_id = brainshop.get("brain_id")
        self.api_key = brainshop.get("api_key")

    async def get_response(
        self, author: Union[discord.User, discord.Member], message: str
    ) -> Optional[str]:
        """
        Get a response from the chatbot.
        """
        params = {
            "bid": self.brain_id,
            "key": self.api_key,
            "uid": author.id,
            "msg": message,
        }
        async with self.session.get("http://api.brainshop.ai/get", params=params) as resp:
            if resp.status != 200:
                return
            resp_data = await resp.json()
            status = resp_data.get("status") or "success"
            if status != "success":
                return
            return resp_data.get("cnt")

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if not await self.bot.allowed_by_whitelist_blacklist(who=message.author):
            return
        if message.author.bot:
            return
        if not message.guild:
            response = await self.get_response(message.author, message.content)
            if response:
                with contextlib.suppress(discord.HTTPException):
                    await message.channel.send(response)
            return
        if not message.channel.permissions_for(message.guild.me).send_messages:
            return
        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return
        guild_settings = await self.config.guild(message.guild).all()
        if message.channel.id not in guild_settings["channels"]:
            if message.content.startswith(
                f"<@!{self.bot.user.id}> "
            ) or message.content.startswith(f"<@{self.bot.user.id}> "):
                if guild_settings["mention"]:
                    response = await self.get_response(
                        message.author, message.clean_content
                    )
                    if response:
                        try:
                            await message.reply(response)
                        except discord.NotFound:
                            await message.channel.send(response)
            else:
                if guild_settings["reply"]:
                    if message.reference is not None:
                        ref_message = await message.channel.fetch_message(
                            message.reference.message_id
                        )
                        if (
                            ref_message is not None
                            and ref_message.author == self.bot.user
                        ):
                            response = await self.get_response(
                                message.author, message.clean_content
                            )
                            if response:
                                try:
                                    await message.reply(response)
                                except discord.NotFound:
                                    await message.channel.send(response)
        else:
            response = await self.get_response(message.author, message.clean_content)
            if response:
                await message.channel.send(response)

    @commands.command(aliases=["chat", "ai", "chatbot", "robot"])
    async def talk(self, ctx: Context, *, message: str):
        """
        Talk to a robot!
        """
        async with ctx.typing():
            response = await self.get_response(ctx.author, message)
            if response is None:
                await ctx.send("Something went wrong. Please try again later.")
            else:
                try:
                    await ctx.reply(response)
                except discord.NotFound:
                    await ctx.send(response)

    @commands.group()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def chatbotset(self, ctx: Context):
        """
        Configure settings about the chatbot.
        """
        pass

    @chatbotset.command()
    async def mention(self, ctx: Context):
        """
        Toggle whether the bot will reply when being mentioned in this guild.
        """
        mention = await self.config.guild(ctx.guild).mention()
        await self.config.guild(ctx.guild).mention.set(not mention)
        if mention:
            await ctx.send("I will no longer reply when mentioned.")
        else:
            await ctx.send("I will now reply when mentioned.")

    @chatbotset.command()
    async def reply(self, ctx: Context):
        """
        Toggle whether the bot will reply when being replied to in this guild.
        """
        reply = await self.config.guild(ctx.guild).reply()
        await self.config.guild(ctx.guild).reply.set(not reply)
        if reply:
            await ctx.send("I will no longer reply to messages.")
        else:
            await ctx.send("I will now reply to messages.")

    @chatbotset.group(name="channels", aliases=["channel"])
    async def chatbotset_channels(self, ctx: Context):
        """
        Set the channels that the chatbot will respond in.
        """
        pass

    @chatbotset_channels.command(name="add")
    async def chatbotset_channels_add(self, ctx: Context, channel: discord.TextChannel):
        """
        Add a channel that the chatbot will respond in.
        """
        channel_list = await self.config.guild(ctx.guild).channels()
        if channel.id not in channel_list:
            channel_list.append(channel.id)
            await self.config.guild(ctx.guild).channels.set(channel_list)
            await ctx.tick()
        else:
            await ctx.send(f"That channel is already set as a chatbot channel.")

    @chatbotset_channels.command(name="remove")
    async def chatbotset_channels_remove(
        self, ctx: Context, channel: discord.TextChannel
    ):
        """
        Remove a channel that the chatbot will respond in.
        """
        channel_list = await self.config.guild(ctx.guild).channels()
        if channel.id in channel_list:
            channel_list.remove(channel.id)
            await self.config.guild(ctx.guild).channels.set(channel_list)
            await ctx.tick()
        else:
            await ctx.send(f"That channel wasn't set as a chatbot channel.")

    @chatbotset_channels.command(name="clear")
    async def chatbotset_channels_clear(self, ctx: Context):
        """
        Clear all the channels that the chatbot will respond in.
        """
        channel_list = await self.config.guild(ctx.guild).channels()
        if not channel_list:
            await ctx.send("There are no chatbot channels set.")
            return

        m = await ctx.send(
            "Are you sure you want to clear all the channels that the ai talks in? Respond with yes or no."
        )

        start_adding_reactions(m, ReactionPredicate.YES_OR_NO_EMOJIS)
        pred = ReactionPredicate.yes_or_no(m, ctx.author)
        try:
            await ctx.bot.wait_for("reaction_add", check=pred, timeout=60)
        except asyncio.TimeoutError:
            with contextlib.suppress(discord.NotFound):
                await m.delete()
            return

        if pred.result:
            await self.config.guild(ctx.guild).channels.clear()
            await ctx.tick()
        else:
            await ctx.send("Ok, aborted.")

    @chatbotset_channels.command(name="list")
    async def chatbotset_channels_list(self, ctx: Context):
        """
        List all the channels that the chatbot will respond in.
        """
        channel_list = await self.config.guild(ctx.guild).channels()
        if not channel_list:
            await ctx.send("There are no chatbot channels set.")
            return

        text = "".join(
            "<#" + str(channel) + "> - " + str(channel) + "\n" for channel in channel_list
        )
        pages = [p for p in pagify(text=text, delims="\n")]
        embeds = []
        for index, page in enumerate(pages):
            embed = discord.Embed(
                title="ChatBot Channels",
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
