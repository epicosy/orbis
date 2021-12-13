import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple

from cement import Handler

from orbis.data.misc import Context
from orbis.data.results import CommandData
from orbis.data.schema import Oracle
from orbis.ext.database import TestOutcome
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

    def set(self, **kwargs):
        """Sets the env variables for the operations."""
        self.env["MAVEN_HOME"] = self.get_config("maven_home")
        self.env["JAVA_HOME"] = self.get_config("java8_home")
        self.env["PATH"] += ":" + self.get_config("maven_home") + "/bin"

    def checkout(self, vid: str, handler: CheckoutHandler, working_dir: str = None,
                 root_dir: str = None, **kwargs) -> Dict[str, Any]:

        project = self.get_by_vid(vid)
        manifest = project.get_manifest(vid)
        corpus_path = Path(self.get_config('corpus'))  # benchmark repository path

        iid, working_dir = handler(project, manifest=manifest, corpus_path=corpus_path,
                                   working_dir=working_dir, root_dir=root_dir)

        return {'iid': iid, 'working_dir': str(working_dir.resolve())}

    def build(self, context: Context, handler: BuildHandler, **kwargs) -> Tuple[CommandData, Path]:
        build_handler = self.app.handler.get('handlers', 'java_build', setup=True)
        manifest = context.project.get_version(sha=context.instance.sha)

        if manifest.vuln.build.system == "Maven":
            cmd_data = build_handler.build_maven(context, self.env)
        elif manifest.vuln.build.system == "Gradle":
            cmd_data = build_handler.build_gradle(context, self.env)
        else:
            cmd_data = CommandData(args="")
        return cmd_data, Path(context.root)

    def test(self, context: Context, handler: TestHandler, tests: Oracle, timeout: int,
             **kwargs) -> List[TestOutcome]:
        test_handler = self.app.handler.get('handlers', 'java_test', setup=True)
        manifest = context.project.get_version(sha=context.instance.sha)

        test_outcomes = []
        for name, test in tests.cases.items():
            if manifest.vuln.build.system == "Maven":
                cmd_data, outcome = test_handler.test_maven(context, manifest.vuln.build, test, self.env)
                test_outcomes.append(outcome.to_dict())
            elif manifest.vuln.build.system == "Gradle":
                cmd_data, outcome = test_handler.test_gradle(context, manifest.vuln.build, test, self.env)
                test_outcomes.append(outcome.to_dict())

        return test_outcomes

    def make(self, context: Context, handler: Handler, **kwargs) -> CommandData:
        pass


def load(nexus):
    nexus.handler.register(VUL4J)
