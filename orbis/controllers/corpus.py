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
            (['--vid'], {'help': 'The vulnerability id.', 'type': str, 'required': True}),
        ]

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
        benchmark_handler = self.app.handler.get('handlers', self.app.plugin.benchmark, setup=True)

        if self._parser.unknown_args:
            benchmark_handler.checkout(**vars(self.app.pargs), **self._parser.unknown_args)
        else:
            benchmark_handler.checkout(**vars(self.app.pargs))

        # if checkout_handler.error:
        #    self.app.log.error(checkout_handler.error)
