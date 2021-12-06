import re
from pathlib import Path
from typing import Union, List, Dict, Any, AnyStr, Tuple

from cement import Handler

from orbis.core.exc import OrbisError
from orbis.data.misc import Context
from orbis.data.results import CommandData
from orbis.data.schema import Oracle, Program, Paths, Vulnerability
from orbis.ext.database import TestOutcome, Instance
from orbis.handlers.benchmark import BenchmarkHandler
from orbis.handlers.operations.build import BuildHandler
from orbis.handlers.operations.checkout import CheckoutHandler
from orbis.handlers.operations.test import TestHandler


class VUL4J(BenchmarkHandler):
    """
        Handler for interacting locally with the Vul4J benchmark
    """

    class Meta:
        label = 'vul4j'

    def get_context(self, iid: int) -> Context:
        instance = self.app.db.query(Instance, iid)
        working_dir = Path(instance.path)
        commit_sha = instance.sha
        project = self.get_by_commit_sha(commit_sha)
        manifest = project.get_manifest_by_commit_sha(commit_sha)

        program = Program(name="", id="", manifest=list(), paths=Paths(source="", lib="", include=""))
        return Context(instance=instance, root=working_dir,

                       project=project, manifest=manifest,

                       source=working_dir / Path("src"), program=program,
                       build=working_dir / Path("build")
                       )

    def set(self, **kwargs):
        """Sets the env variables for the operations."""
        pass

    def checkout(self, vid: str, handler: CheckoutHandler, working_dir: str = None,
                 root_dir: str = None, **kwargs) -> Dict[str, Any]:

        project = self.get_by_vid(vid)
        manifest = project.get_manifest(vid)
        corpus_path = Path(self.get_configs()['paths']['corpus'])  # benchmark repository path

        iid, working_dir = handler(project, manifest=manifest, corpus_path=corpus_path,
                                            working_dir=working_dir, root_dir=root_dir)

        return {'iid': iid, 'working_dir': str(working_dir.resolve())}

    def build(self, context: Context, handler: BuildHandler, **kwargs) -> Tuple[CommandData, Path]:
        build_handler = self.app.handler.get('handlers', 'java_build', setup=True)

        if context.manifest.vuln.build_system == "Maven":
            cmd_data = build_handler.build_maven(context, self.env)
        elif context.manifest.vuln.build_system == "Gradle":
            cmd_data = build_handler.build_gradle(context, self.env)
        else:
            cmd_data = CommandData(args="")
        return cmd_data, Path(context.root)

    def test(self, context: Context, handler: TestHandler, tests: Oracle, timeout: int,
             **kwargs) -> List[TestOutcome]:
        test_handler = self.app.handler.get('handlers', 'java_test', setup=True)

        test_outcomes = []

        if context.manifest.vuln.build_system == "Maven":
            cmd_data = test_handler.test_maven(context, self.env)
        elif context.manifest.vuln.build_system == "Gradle":
            cmd_data = test_handler.test_gradle(context, self.env)

        return test_outcomes

    def make(self, context: Context, handler: Handler, **kwargs) -> CommandData:
        pass


def load(nexus):
    nexus.handler.register(VUL4J)
