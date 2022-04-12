from abc import abstractmethod
from os import environ
from pathlib import Path
from typing import List

from cement import Handler

from orbis.core.exc import OrbisError
from orbis.data.misc import Context
from orbis.data.results import CommandData
from orbis.data.schema import Project, Oracle, parse_dataset, Vulnerability
from orbis.ext.database import Instance
from orbis.handlers.command import CommandHandler
from orbis.handlers.operations.checkout import CheckoutHandler


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
        margin = self.get_config('testing')['margin']

        if value:
            return value + margin

        return self.get_config('testing')['timeout'] + margin

    def get_config(self, key: str):
        return self.app.config.get(self.Meta.label, key)

    def get_configs(self):
        return self.app.config.get_section_dict(self.Meta.label).copy()
    
    def get_projects(self, load: bool = True) -> List[Project]:
        """
            Returns the projects in the dataset
        """
        dataset = self.get_config('dataset')
        corpus_path = Path(self.get_config('corpus'))
        projects = parse_dataset(dataset, corpus_path=corpus_path)

        if load:
            for project in projects:
                project.load_oracles()

        return projects

    def get_vulns(self) -> List[Vulnerability]:
        """
            Returns the vulnerabilities in the dataset
        """
        vulns = []

        for p in self.get_projects():
            for m in p.manifest:
                m.vuln.pid = p.id
                vulns.append(m.vuln)

        return vulns

    def get_vuln(self, vid: str) -> Vulnerability:
        for project in self.get_projects():
            for m in project.manifest:
                if m.vuln.id == vid:
                    m.vuln.pid = project.id
                    return m.vuln

    def get_by_vid(self, vid: str) -> Project:
        for project in self.get_projects():
            for m in project.manifest:
                if m.vuln.id == vid:
                    return project

        raise OrbisError(f"Project with vulnerability id {vid} not found")

    def get_by_commit_sha(self, commit_sha: str) -> Project:
        for project in self.get_projects():
            for m in project.manifest:
                if m.commit == commit_sha:
                    return project

        raise OrbisError(f"Project with commit sha {commit_sha} not found")

    def has(self, pid: str) -> bool:
        return pid in [p.id for p in self.get_projects()]

    def get(self, pid: str) -> Project:
        for p in self.get_projects():

            if p.id == pid:
                return p

        raise OrbisError(f"Program with {pid} not found")

    def get_context(self, iid: int) -> Context:
        instance = self.app.db.query(Instance, iid)
        working_dir = Path(instance.path)
        project = self.get_by_commit_sha(instance.sha)

        return Context(instance=instance, root=working_dir, source=working_dir / project.name, project=project,
                       build=working_dir / Path("build"))

    @property
    def checkout_handler(self) -> CheckoutHandler:
        return self.app.handler.get('handlers', 'checkout', setup=True)

    @abstractmethod
    def checkout(self, vid: str, working_dir: str, **kwargs) -> CommandData:
        """Checks out the program to the working directory"""
        pass

    @abstractmethod
    def build(self, handler: Handler, context: Context, **kwargs) -> CommandData:
        pass

    @abstractmethod
    def test(self, handler: Handler, context: Context, tests: Oracle, timeout: int,
             **kwargs) -> CommandData:
        pass

    @abstractmethod
    def gen_tests(self, project: Project, **kwargs) -> CommandData:
        pass
