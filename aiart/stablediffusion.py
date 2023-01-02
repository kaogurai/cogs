import asyncio
import base64
import contextlib
import random
import string
from typing import Optional

import aiohttp
import discord
from aiohttp.client import _WSRequestContextManager
from redbot.core import commands
from redbot.core.commands import Context

from .abc import MixinMeta


class StableDiffusionCommand(MixinMeta):

    # @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def stablediffusion(self, ctx: Context, *, text: str):
        """
        Generate art using Stable Diffusion.
        """
