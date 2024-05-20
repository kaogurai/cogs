from abc import ABC

import aiohttp
from redbot.core import Config, commands
from redbot.core.bot import Red


class MixinMeta(ABC):
    def __init__(self, *args) -> None:
        self.config: Config
        self.bot: Red
        self.session: aiohttp.ClientSession


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    ...
