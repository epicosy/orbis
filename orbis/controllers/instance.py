from cement import Controller, ex

from orbis.core.exc import OrbisError
from cement.ext.ext_argparse import ArgparseArgumentHandler


make_args = [
    (['-wba', '--write_build_args'], {'help': 'File to output build args.', 'type': str, 'default': None}),
    (['-ee', '--exit_err'], {'help': 'Exits when error occurred.', 'action': 'store_false', 'required': False}),
    (['-T', '--tag'], {'help': 'Flag for tracking sanity check.', 'action': 'store_true', 'required': False}),
    (['-wd', '--working_dir'], {'help': 'Overwrites the working directory to the specified path', 'type': str,
                                'required': False})
]


argparse_handler = ArgparseArgumentHandler(add_help=False)
argparse_handler.Meta.ignore_unknown_arguments = True

# Exclusive arguments for test command
test_argparse_handler = ArgparseArgumentHandler(add_help=False)
tests_group = test_argparse_handler.add_mutually_exclusive_group(required=False)
tests_group.add_argument('--tests', type=str, nargs='+', help='Run all tests.', required=False)
tests_group.add_argument('--povs', type=str, nargs='+', help='Run all povs.', required=False)


class Instance(Controller):
    class Meta:
        label = 'instance'
        stacked_on = 'base'
        stacked_type = 'nested'

        arguments = [
            (['--id'], {'help': 'The id of the instance (challenge checked out).', 'type': int, 'required': True}),
        ]
        
        parents=[argparse_handler]


    def _post_argument_parsing(self):
        self.benchmark_handler = self.app.handler.get('handlers', self.app.plugin.benchmark, setup=True)
        # TODO: fix this
        self.args = vars(self.app.args.parsed_args)
        self.unk = self.app.args.unknown_args if self.app.args.unknown_args else []

        if 'id' in self.app.pargs:
            self.context = self.benchmark_handler.get_context(self.app.pargs.id)

            if not self.context:
                raise OrbisError(f"No instance {self.app.pargs.id} found. Use the ID supplied by the checkout command")

            if not self.context.root:
                raise OrbisError('Working directory is required. Checkout again the working directory')

            if not self.context.root.exists():
                raise OrbisError('Working directory does not exist.')

    @ex(
        help='Cmake init of the Makefiles.',
        arguments=make_args,
    )
    def make(self):
        make_handler = self.app.handler.get('handlers', 'make', setup=True)
        self.benchmark_handler.set()
        self.benchmark_handler.make(context=self.context, handler=make_handler, **self.args)
        self.benchmark_handler.unset()
    
    @ex(
        help='Build the instance.',
        arguments=make_args,
    )
    def build(self):
        build_handler = self.app.handler.get('handlers', 'build', setup=True)
        self.benchmark_handler.set()
        cmd_data, _ = self.benchmark_handler.build(context=self.context, handler=build_handler, **self.args)
        build_handler.save_outcome(cmd_data, self.context)
        self.benchmark_handler.unset()

    @ex(
        help='Tests the instance.',
        arguments=[
            (['-T', '--timeout'], {'help': 'Timeout for the tests.', 'required': False, 'type': int}),
        ],
        parents=[test_argparse_handler]
    )
    def test(self):
        test_handler = self.app.handler.get('handlers', 'test', setup=True)
        
        if self.app.pargs.povs:
            tests = self.benchmark_handler.get_oracle(self.context.program, self.app.pargs.povs, True)
        else:
            tests = self.benchmark_handler.get_oracle(self.context.program, self.app.pargs.tests)

        timeout_margin = self.benchmark_handler.get_test_timeout_margin()
        timeout = self.app.pargs.timeout if self.app.pargs.timeout else timeout_margin
        # TODO: fix this
        del self.args['timeout']
        del self.args['tests']
        self.benchmark_handler.set()
        self.benchmark_handler.test(context=self.context, handler=test_handler, tests=tests, timeout=timeout, **self.args)
        self.benchmark_handler.unset()
