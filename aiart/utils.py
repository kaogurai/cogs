import argparse

from redbot.core.commands import BadArgument


class NoExitParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise BadArgument()
