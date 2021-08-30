from abc import abstractmethod
from binascii import b2a_hex
from os import urandom
from pathlib import Path
from typing import List, AnyStr, Dict

from orbis.data.results import CommandData, Program
from orbis.handlers.command import CommandHandler


class BenchmarkHandler(CommandHandler):
    class Meta:
        label = 'benchmark'

    def __call__(self, cmd_str, args: str = "", call: bool = True, **kwargs) -> CommandData:
        cmd_data = CommandData(f"{cmd_str} {args}" if args else cmd_str)

        if call:
            return super().__call__(cmd_data=cmd_data, **kwargs)

        return cmd_data

    def get_config(self, key: str):
        return self.app.config.get(self.Meta.label, key)

    def get_configs(self):
        return self.app.config.get_section_dict(self.Meta.label).copy()

    # TODO: connect to a volume
    def get_working_dir(self, program_name: str, randomize: bool = False) -> Path:
        container_handler = self.app.handler.get('manager', 'benchmark', setup=True)
        container_data = container_handler.get_container_data(self.Meta.label)
        working_dir = Path(f"/{container_data.volume}", program_name)

        if randomize:
            working_dir = working_dir.parent / (working_dir.name + "_" + b2a_hex(urandom(2)).decode())

        return Path(working_dir)

    @abstractmethod
    def get_manifest(self, program: Program, **kwargs) -> List[str]:
        pass

    @abstractmethod
    def get_programs(self, **kwargs):
        """Gets the benchmark's programs"""
        pass

    @abstractmethod
    def checkout(self, program: Program, **kwargs) -> CommandData:
        """Checks out the program to the working directory"""
        pass

    @abstractmethod
    def make(self, program: Program, **kwargs) -> CommandData:
        pass

    @abstractmethod
    def compile(self, program: Program, **kwargs) -> CommandData:
        pass

    @abstractmethod
    def test(self, program: Program, **kwargs) -> CommandData:
        pass
