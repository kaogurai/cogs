import asyncio
import datetime
import urllib
from io import BytesIO

import discord
from redbot.core import commands
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .abc import MixinMeta


class RolesMixin(MixinMeta):
    ...
