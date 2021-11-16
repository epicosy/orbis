from cement import Controller, ex
from cement.ext.ext_argparse import ArgparseArgumentHandler


argparse_handler = ArgparseArgumentHandler(add_help=False)
argparse_handler.Meta.ignore_unknown_arguments = True


class Corpus(Controller):
    class Meta:
        label = 'corpus'
        stacked_on = 'base'
        stacked_type = 'nested'

        arguments = [
            (['--pid'], {'help': 'The program id.', 'type': str, 'required': True}),
        ]

    def _pre_argument_parsing(self):
        self.benchmark_handler = self.app.handler.get('handlers', self.app.plugin.benchmark, setup=True)

    @ex(
        help='Checks out the specified challenge to a working directory.',
        arguments=[
            (['-wd', '--working_directory'], {'help': 'The working directory.', 'type': str, 'required': False,
                                              'dest': 'working_dir'}),
            (['-rd', '--root_dir'], {'help': 'The root directory used for the working directory.', 'type': str,
                                     'required': False}),
            (['-S', '--seed'], {'help': "Random seed", 'required': False, 'type': int}),
            (['-F', '--force'], {'help': "Forces to checkout to existing directory", 'required': False,
                                 'action': 'store_true'})
        ],
        parents=[argparse_handler]
    )
    def checkout(self):
        checkout_handler = self.app.handler.get('handlers', 'checkout', setup=True)
        print(self._parser.unknown_args)
        if self._parser.unknown_args:
            self.benchmark_handler.checkout(handler=checkout_handler, **vars(self.app.pargs), 
                                            **self._parser.unknown_args)
        else:
            self.benchmark_handler.checkout(handler=checkout_handler, **vars(self.app.pargs))

        # if checkout_handler.error:
        #    self.app.log.error(checkout_handler.error)
