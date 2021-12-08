from abc import ABC

from redbot.core import Config
from redbot.core.bot import Red


class MixinMeta(ABC):
    """
    Idk what this does, but it's in lastfm's ABC
    """

    def __init__(self, *_args):
        self.config: Config
        self.bot: Red
