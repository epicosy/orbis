from abc import abstractmethod
from os import environ
from pathlib import Path
import yaml
from typing import List, Union

from cement import Handler

from orbis.core.exc import OrbisError
from orbis.data.misc import Context
from orbis.data.results import CommandData
from orbis.data.schema import Program, Oracle, parse_oracle
from orbis.data.schema import parse_metadata
from orbis.ext.database import Instance
from orbis.handlers.command import CommandHandler


def args_to_str(args: dict) -> str:
    arg_str = ""

    for opt, arg in args.items():
        if isinstance(arg, dict):
            arg_str += args_to_str(arg)
            continue
        arg_str += f" {opt} {arg}" if arg else f" {opt}"

    return arg_str


class BenchmarkHandler(CommandHandler):
    class Meta:
        label = 'benchmark'

    def __init__(self, **kw):
        super().__init__(**kw)
        self.env = environ.copy()

    @abstractmethod
    def set(self, **kwargs):
        """Sets the env variables for the operations."""
        pass

    def unset(self):
        """Unsets the env variables."""
        self.env = environ.copy()

    #    def __call__(self, cmd_str, args: dict = None, call: bool = True, **kwargs) -> CommandData:
    #        cmd_data = CommandData(f"{cmd_str} {args_to_str(args)}" if args else cmd_str)

    #        if call:
    #            return super().__call__(cmd_data=cmd_data, **kwargs)

    #        return cmd_data

    def get_test_timeout_margin(self, value: int = None):
        margin = self.get_config('tests')['margin']

        if value:
            return value + margin

        return self.get_config('tests')['timeout'] + margin

    def get_config(self, key: str):
        return self.app.config.get(self.Meta.label, key)

    def get_configs(self):
        return self.app.config.get_section_dict(self.Meta.label).copy()

    def has(self, pid: str) -> bool:
        return pid in [p.id for p in self.all()]

    def get(self, pid: str) -> Program:
        for p in self.all():

            if p.id == pid:
                return p

        raise OrbisError(f"Program with {pid} not found")

    def get_oracle(self, program: Program, cases: List[str], pov: bool = False) -> Union[Oracle, None]:
        if pov:
            oracle_file = Path(self.get_config('paths')['povs']) / program.name / '.povs'
        else:
            oracle_file = Path(self.get_config('paths')['tests']) / program.name / '.tests'

        if not oracle_file.exists():
            # self.app.log.debug(f"Oracle file not found in {oracle_file.parent}")
            return None
            # raise OrbisError(f"Metadata file not found in {program_path}")

        with oracle_file.open(mode="r") as stream:
            return parse_oracle(yaml.safe_load(stream), cases, pov)

    def all(self) -> List[Program]:
        corpus_path = Path(self.get_config('paths')['corpus'])
        return list(filter(None, [self.load(d) for d in corpus_path.iterdir() if d.is_dir()]))

    def load(self, program_path: Path) -> Union[Program, None]:
        metadata_file = program_path / '.metadata'

        if not metadata_file.exists():
            #self.app.log.debug(f"Metadata file not found in {program_path}")
            return None
            # raise OrbisError(f"Metadata file not found in {program_path}")

        with metadata_file.open(mode="r") as stream:
            return parse_metadata(yaml.safe_load(stream))

    def get_context(self, iid: int) -> Context:
        instance = self.app.db.query(Instance, iid)
        working_dir = Path(instance.path)
        program = self.get(instance.pid)

        return Context(instance=instance, root=working_dir, source=working_dir / program.name, program=program,
                       build=working_dir / Path("build"))

    @abstractmethod
    def checkout(self, pid: str, working_dir: str, **kwargs) -> CommandData:
        """Checks out the program to the working directory"""
        pass

    @abstractmethod
    def make(self, context: Context, handler: Handler, **kwargs) -> CommandData:
        pass

    @abstractmethod
    def build(self, context: Context, handler: Handler, **kwargs) -> CommandData:
        pass

    @abstractmethod
    def test(self, context: Context, handler: Handler, tests: Oracle, povs: Oracle, timeout: int,
             **kwargs) -> CommandData:
        pass
