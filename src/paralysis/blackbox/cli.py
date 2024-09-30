from dataclasses import dataclass

from jsonargparse import CLI

@dataclass
class CommandLine:
    round_min: int | None
    round_max: int | None
    
    def meta_stats(self):
        pass


def command():
    CLI(CommandLine, as_positional=False)
