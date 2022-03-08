from cement import Controller, ex
from cement.utils.version import get_version_banner
from ..core.version import get_version
from git import Repo
from pathlib import Path

VERSION_BANNER = """
API Framework for benchmarking databases of vulnerabilities for controlled testing studies %s
%s
""" % (get_version(), get_version_banner())


class Base(Controller):
    class Meta:
        label = 'base'

        # text displayed at the top of --help output
        description = 'API Framework for benchmarking databases of vulnerabilities for controlled testing studies'

        # text displayed at the bottom of --help output
        epilog = 'Usage: orbis --help'

        # controller level arguments. ex: 'orbis --version'
        arguments = [
            (['-v', '--version'], {'action': 'version', 'version': VERSION_BANNER}),
            (['-vb', '--verbose'], {'help': 'Verbose output.', 'action': 'store_true'})
        ]

    def _default(self):
        """Default action if no sub-command is passed."""

        self.app.args.print_help()

    @ex(
        help='Launches the server API',
        arguments=[
            (['-p', '--port'], {'help': 'Port for server. (Overwrites config port)', 'type': int, 'required': False}),
            (['-a', '--address'], {'help': 'IPv4 host address for server. ', 'type': str, 'default': '0.0.0.0'})
        ]
    )
    def api(self):
        """
            Launches REST API
        """
        port = self.app.get_config('api')['port']

        if self.app.pargs.port:
            port = self.app.pargs.port

        self.app.api.run(debug=True, port=port, host=self.app.pargs.address)

    @ex(
        help='Inits the projects in the dataset.',
        arguments=[]
    )
    def init(self):
        """
            Inits the projects in the dataset
        """
        benchmark_handler = self.app.handler.get('handlers', self.app.plugin.benchmark, setup=True)

        for proj in benchmark_handler.get_projects(load=False):
            project_name = proj.repo_path.split('/')[-1]
            project_path = Path(benchmark_handler.get_config('corpus'), project_name)

            if project_path.exists():
                repo = Repo(str(project_path))

                if repo.bare:
                    self.app.log.warning(f"Bare repo {proj.repo_path}")
            else:
                repo = Repo.clone_from(f"https://github.com/{proj.repo_path}", str(project_path))
                self.app.log.info(f"Cloned {proj.repo_path}")
